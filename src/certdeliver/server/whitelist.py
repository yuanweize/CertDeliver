"""
Whitelist management for CertDeliver server.
Validates client IPs against resolved domain names.
"""

import socket
import asyncio
import logging
from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WhitelistManager:
    """
    Manages IP whitelist based on domain name resolution.
    
    Caches resolved IPs and refreshes them periodically.
    """
    
    def __init__(
        self,
        domains: List[str],
        cache_ttl_seconds: int = 300,
        enable_ipv6: bool = False
    ):
        """
        Initialize the whitelist manager.
        
        Args:
            domains: List of domain names to whitelist.
            cache_ttl_seconds: Cache TTL in seconds (default: 5 minutes).
            enable_ipv6: Include IPv6 addresses (default: False).
        """
        self.domains = domains
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.enable_ipv6 = enable_ipv6
        
        self._cache: Dict[str, Set[str]] = {}
        self._last_update: Optional[datetime] = None
        self._lock = asyncio.Lock()
    
    @property
    def is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if self._last_update is None:
            return False
        return datetime.now() - self._last_update < self.cache_ttl
    
    def _resolve_domain_sync(self, domain: str) -> Set[str]:
        """
        Synchronously resolve a domain to IP addresses.
        
        Args:
            domain: Domain name to resolve.
        
        Returns:
            Set of resolved IP addresses.
        """
        ips: Set[str] = set()
        
        try:
            # Get all address info for the domain
            addr_info = socket.getaddrinfo(
                domain, None,
                socket.AF_UNSPEC if self.enable_ipv6 else socket.AF_INET
            )
            
            for info in addr_info:
                ip = info[4][0]
                ips.add(ip)
                
        except socket.gaierror as e:
            logger.warning(f"Failed to resolve domain {domain}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error resolving {domain}: {e}")
        
        return ips
    
    async def _resolve_domain(self, domain: str) -> Set[str]:
        """
        Asynchronously resolve a domain to IP addresses.
        
        Args:
            domain: Domain name to resolve.
        
        Returns:
            Set of resolved IP addresses.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._resolve_domain_sync,
            domain
        )
    
    async def refresh_cache(self, force: bool = False) -> None:
        """
        Refresh the IP cache by resolving all domains.
        
        Args:
            force: Force refresh even if cache is valid.
        """
        if not force and self.is_cache_valid:
            return
        
        async with self._lock:
            # Double-check after acquiring lock
            if not force and self.is_cache_valid:
                return
            
            logger.info("Refreshing whitelist cache...")
            
            new_cache: Dict[str, Set[str]] = {}
            
            # Resolve all domains concurrently
            tasks = [
                self._resolve_domain(domain)
                for domain in self.domains
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for domain, result in zip(self.domains, results):
                if isinstance(result, Exception):
                    logger.error(f"Error resolving {domain}: {result}")
                    # Keep old cache entry if available
                    if domain in self._cache:
                        new_cache[domain] = self._cache[domain]
                else:
                    new_cache[domain] = result
            
            self._cache = new_cache
            self._last_update = datetime.now()
            
            total_ips = sum(len(ips) for ips in self._cache.values())
            logger.info(
                f"Whitelist cache refreshed: {len(self.domains)} domains, "
                f"{total_ips} IPs"
            )
    
    def refresh_cache_sync(self, force: bool = False) -> None:
        """
        Synchronously refresh the IP cache.
        
        Args:
            force: Force refresh even if cache is valid.
        """
        if not force and self.is_cache_valid:
            return
        
        logger.info("Refreshing whitelist cache (sync)...")
        
        new_cache: Dict[str, Set[str]] = {}
        
        for domain in self.domains:
            new_cache[domain] = self._resolve_domain_sync(domain)
        
        self._cache = new_cache
        self._last_update = datetime.now()
    
    async def is_whitelisted(self, client_ip: str) -> bool:
        """
        Check if a client IP is in the whitelist.
        
        Args:
            client_ip: The client IP address to check.
        
        Returns:
            True if whitelisted, False otherwise.
        """
        # Ensure cache is up to date
        await self.refresh_cache()
        
        # Check all cached IPs
        for domain, ips in self._cache.items():
            if client_ip in ips:
                logger.debug(f"IP {client_ip} matched domain {domain}")
                return True
        
        # IP not found, try force refresh once
        await self.refresh_cache(force=True)
        
        for domain, ips in self._cache.items():
            if client_ip in ips:
                logger.info(
                    f"IP {client_ip} matched domain {domain} after refresh"
                )
                return True
        
        logger.warning(f"IP {client_ip} not in whitelist")
        return False
    
    def is_whitelisted_sync(self, client_ip: str) -> bool:
        """
        Synchronously check if a client IP is in the whitelist.
        
        Args:
            client_ip: The client IP address to check.
        
        Returns:
            True if whitelisted, False otherwise.
        """
        self.refresh_cache_sync()
        
        for domain, ips in self._cache.items():
            if client_ip in ips:
                return True
        
        # Try force refresh
        self.refresh_cache_sync(force=True)
        
        for ips in self._cache.values():
            if client_ip in ips:
                return True
        
        return False
    
    def get_all_whitelisted_ips(self) -> Set[str]:
        """Get all currently whitelisted IPs."""
        all_ips: Set[str] = set()
        for ips in self._cache.values():
            all_ips.update(ips)
        return all_ips
    
    def get_cache_info(self) -> dict:
        """Get cache status information."""
        return {
            "domains": self.domains,
            "cached_domains": list(self._cache.keys()),
            "total_ips": sum(len(ips) for ips in self._cache.values()),
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "cache_valid": self.is_cache_valid,
            "cache_ttl_seconds": self.cache_ttl.total_seconds(),
        }
