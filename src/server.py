"""Metrics server for real-time monitoring"""

import asyncio
import json
import socket
from datetime import datetime
from aiohttp import web, WSMsgType
from typing import Set, Dict, Any, Optional

class MetricsServer:
    def __init__(self, port: int = 8088):
        self.port = port
        self.app = web.Application()
        self.websockets: Set[web.WebSocketResponse] = set()
        self.runner = None
        self.site = None
        
        # Current metrics cache
        self.current_metrics = {
            "concurrency": 0,
            "queue_depth": 0,
            "throughput_rps": 0.0,
            "p50_ms": 0,
            "p95_ms": 0,
            "error_rate": 0.0,
            "tokens_per_sec_in": 0.0,
            "tokens_per_sec_out": 0.0,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/metrics', self.get_metrics)
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_get('/health', self.health_check)
        
    async def start(self):
        """Start metrics server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, 'localhost', self.port)
        await self.site.start()
        
        print(f"Metrics server started on http://localhost:{self.port}")
        
    async def stop(self):
        """Stop metrics server"""
        # Close all websockets
        for ws in self.websockets.copy():
            await ws.close()
            
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
            
    async def get_metrics(self, request):
        """HTTP endpoint for current metrics"""
        return web.json_response(self.current_metrics)
        
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({"status": "ok", "timestamp": datetime.utcnow().isoformat()})
        
    async def websocket_handler(self, request):
        """WebSocket handler for real-time metrics"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        
        try:
            # Send current metrics immediately
            await ws.send_str(json.dumps({
                "type": "metrics",
                "data": self.current_metrics
            }))
            
            # Keep connection alive
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    print(f'WebSocket error: {ws.exception()}')
                    break
                    
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            self.websockets.discard(ws)
            
        return ws
        
    async def update_metrics(self, metrics: Dict[str, Any]):
        """Update current metrics and broadcast to websockets"""
        self.current_metrics.update(metrics)
        self.current_metrics["last_updated"] = datetime.utcnow().isoformat()
        
        # Broadcast to all connected websockets
        if self.websockets:
            message = json.dumps({
                "type": "metrics",
                "data": self.current_metrics
            })
            
            # Send to all websockets, remove closed ones
            closed_ws = set()
            for ws in self.websockets:
                try:
                    await ws.send_str(message)
                except Exception:
                    closed_ws.add(ws)
                    
            # Clean up closed websockets
            self.websockets -= closed_ws