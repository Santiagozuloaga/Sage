"""
SAGE OS v4.5 Web Interface Server

FastAPI server providing REST API and WebSocket for web interface.
This is a presentation layer over the existing runtime - no architecture changes.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn


logger = logging.getLogger(__name__)


class WebServer:
    """
    Web server for SAGE OS web interface.
    
    Provides REST API endpoints and WebSocket for real-time updates.
    This is a presentation layer - does not modify kernel or architecture.
    """

    def __init__(self, kernel, host: str = "127.0.0.1", port: int = 8000):
        self.kernel = kernel
        self.host = host
        self.port = port
        self.app = FastAPI(title="SAGE OS v4.5", version="4.5")
        self.websocket_connections: list[WebSocket] = []
        self._setup_routes()
        self._setup_static_files()

    def _setup_static_files(self):
        """Setup static file serving."""
        static_dir = Path(__file__).parent / "static"
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Serve main HTML interface."""
            html_file = Path(__file__).parent / "static" / "index.html"
            if html_file.exists():
                return HTMLResponse(html_file.read_text(encoding="utf-8"))
            return HTMLResponse("<h1>SAGE OS v4.5 - Interface not found</h1>")

        @self.app.get("/api/kernel/status")
        async def get_kernel_status():
            """Get kernel status."""
            if not self.kernel or not self.kernel.context:
                return {"error": "Kernel not initialized"}
            
            return {
                "session_id": self.kernel.session_id,
                "state": self.kernel.state.value,
                "is_running": self.kernel.is_running,
                "command_count": self.kernel.context.command_count,
                "error_count": self.kernel.context.error_count,
                "boot_time": self.kernel.context.boot_time.isoformat(),
                "uptime_seconds": (datetime.now() - self.kernel.context.boot_time).total_seconds()
            }

        @self.app.get("/api/kernel/state")
        async def get_kernel_state():
            """Get kernel state machine state."""
            if not self.kernel or not self.kernel.context:
                return {"error": "Kernel not initialized"}
            
            return {
                "current_state": self.kernel.context.current_state.value,
                "last_transition": {
                    "from": self.kernel.context.last_transition.from_state.value if self.kernel.context.last_transition else None,
                    "to": self.kernel.context.last_transition.to_state.value if self.kernel.context.last_transition else None,
                    "reason": self.kernel.context.last_transition.reason if self.kernel.context.last_transition else None,
                    "timestamp": self.kernel.context.last_transition.timestamp.isoformat() if self.kernel.context.last_transition else None
                } if self.kernel.context.last_transition else None
            }

        @self.app.get("/api/memory/records")
        async def get_memory_records(limit: int = 100):
            """Get engineering memory records."""
            memory = self.kernel.get_component('memory')
            if not memory:
                return {"error": "Memory component not available"}
            
            records = await memory.search_memories(limit=limit)
            return {
                "records": [r.to_dict() for r in records],
                "count": len(records)
            }

        @self.app.get("/api/memory/sessions")
        async def get_memory_sessions():
            """Get session records."""
            memory = self.kernel.get_component('memory')
            if not memory:
                return {"error": "Memory component not available"}
            
            # List sessions by checking runtime state
            sessions = []
            return {"sessions": sessions}

        @self.app.get("/api/mission/active")
        async def get_active_missions():
            """Get active missions."""
            mission_control = self.kernel.get_component('mission_control')
            if not mission_control:
                return {"error": "Mission control not available"}
            
            missions = mission_control.get_active_missions()
            return {"missions": missions}

        @self.app.get("/api/mission/history")
        async def get_mission_history(limit: int = 50):
            """Get mission history."""
            mission_control = self.kernel.get_component('mission_control')
            if not mission_control:
                return {"error": "Mission control not available"}
            
            history = mission_control.get_mission_history(limit)
            return {"history": history}

        @self.app.get("/api/events/history")
        async def get_event_history(limit: int = 100):
            """Get event bus history."""
            event_bus = self.kernel.get_component('event_bus')
            if not event_bus:
                return {"error": "Event bus not available"}
            
            events = event_bus.get_history(limit=limit)
            return {
                "events": [e.to_dict() for e in events],
                "count": len(events)
            }

        @self.app.get("/api/dashboard/status")
        async def get_dashboard_status():
            """Get dashboard system status."""
            dashboard = self.kernel.get_component('dashboard')
            if not dashboard:
                return {"error": "Dashboard not available"}
            
            status = dashboard.get_system_status()
            return status.to_dict()

        @self.app.get("/api/agents/list")
        async def list_agents():
            """List all agents."""
            router = self.kernel.get_component('agent_router')
            if not router:
                return {"error": "Agent router not available"}
            
            agents = router.list_all_agents()
            return {
                "agents": [a.to_dict() for a in agents],
                "count": len(agents)
            }

        @self.app.get("/api/agents/enabled")
        async def list_enabled_agents():
            """List enabled agents."""
            router = self.kernel.get_component('agent_router')
            if not router:
                return {"error": "Agent router not available"}
            
            agents = router.get_enabled_agents()
            return {
                "agents": [a.to_dict() for a in agents],
                "count": len(agents)
            }

        @self.app.post("/api/command/execute")
        async def execute_command(command: Dict[str, str]):
            """Execute a command via the kernel."""
            if not self.kernel:
               return {"error": "Kernel not available"}
            
            cmd = command.get("command", "")
            if not cmd:
                return {"error": "No command provided"}
            
            try:
                result = await self.kernel.execute_command(cmd)
                return {
                    "success": True,
                    "command": cmd,
                    "result": str(result)
                }
            except Exception as e:
                return {
                    "success": False,
                    "command": cmd,
                    "error": str(e)
                }

        @self.app.get("/api/logs/recent")
        async def get_recent_logs(limit: int = 100):
            """Get recent runtime logs."""
            # Placeholder for log retrieval
            return {"logs": [], "count": 0}

        @self.app.get("/api/providers")
        async def get_providers_health():
            """Get health status of all providers."""
            provider_router = self.kernel.get_component('provider_router')
            if not provider_router:
                return {"error": "Provider router not available"}
            
            health_status = await provider_router.get_health_status()
            return health_status

        @self.app.post("/api/chat")
        async def chat(request: Dict[str, Any]):
            """Chat with LLM provider."""
            provider_router = self.kernel.get_component('provider_router')
            if not provider_router:
                return {"error": "Provider router not available"}
            
            provider = request.get("provider", "auto")
            message = request.get("message", "")
            
            if not message:
                return {"error": "No message provided"}
            
            try:
                # Convert single message to chat format
                messages = [{"role": "user", "content": message}]
                response = await provider_router.chat(messages, provider=provider)
                
                return {
                    "success": True,
                    "content": response.content,
                    "provider": response.provider,
                    "model": response.model,
                    "latency_ms": response.latency_ms,
                    "tokens_used": response.tokens_used
                }
            except Exception as e:
                logger.error(f"[WEB] Chat error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.app.post("/api/files/upload")
        async def upload_file(file: UploadFile = File(...)):
            """Upload and process a file."""
            file_processor = self.kernel.get_component('file_processor')
            if not file_processor:
                return {"error": "File processor not available"}
            
            try:
                # Read file data
                file_data = await file.read()
                
                # Process file
                processed = await file_processor.process_file(
                    file_data,
                    file.filename,
                    metadata={"original_filename": file.filename}
                )
                
                # Save to engineering memory
                memory = self.kernel.get_component('memory')
                if memory:
                    await memory.save_memory(
                        memory_type="file",
                        title=processed.filename,
                        content=processed.content,
                        tags=[processed.file_type.value],
                        metadata=processed.metadata
                    )
                
                return {
                    "success": True,
                    "filename": processed.filename,
                    "file_type": processed.file_type.value,
                    "content_preview": processed.content[:500] + "..." if len(processed.content) > 500 else processed.content,
                    "metadata": processed.metadata,
                    "processed_at": processed.processed_at.isoformat()
                }
            except Exception as e:
                logger.error(f"[WEB] File upload error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.app.post("/api/repository/scan")
        async def scan_repository(request: Dict[str, str]):
            """Scan a repository."""
            repo_scanner = self.kernel.get_component('repository_scanner')
            if not repo_scanner:
                return {"error": "Repository scanner not available"}
            
            repo_path = request.get("path", "")
            if not repo_path:
                return {"error": "No repository path provided"}
            
            try:
                from pathlib import Path
                result = await repo_scanner.scan_repository(Path(repo_path))
                
                return {
                    "success": True,
                    "repository_path": result.repository_path,
                    "total_files": result.total_files,
                    "total_lines": result.total_lines,
                    "total_size_kb": result.total_size_bytes / 1024,
                    "languages": result.languages,
                    "summary": result.summary,
                    "scanned_at": result.scanned_at.isoformat()
                }
            except Exception as e:
                logger.error(f"[WEB] Repository scan error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.app.post("/api/audit/run")
        async def run_audit():
            """Run a full system audit."""
            auditor = self.kernel.get_component('auditor')
            if not auditor:
                return {"error": "Auditor not available"}
            
            try:
                report = await auditor.run_full_audit()
                return {
                    "success": True,
                    "report_id": report.report_id,
                    "timestamp": report.timestamp.isoformat(),
                    "summary": report.summary,
                    "passed": report.passed,
                    "issues": [
                        {
                            "severity": issue.severity.value,
                            "component": issue.component,
                            "message": issue.message,
                            "location": issue.location
                        }
                        for issue in report.issues
                    ]
                }
            except Exception as e:
                logger.error(f"[WEB] Audit error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.app.get("/api/audit/history")
        async def get_audit_history(limit: int = 10):
            """Get audit history."""
            auditor = self.kernel.get_component('auditor')
            if not auditor:
                return {"error": "Auditor not available"}
            
            try:
                history = auditor.get_audit_history(limit)
                return {
                    "reports": [
                        {
                            "report_id": report.report_id,
                            "timestamp": report.timestamp.isoformat(),
                            "summary": report.summary,
                            "passed": report.passed
                        }
                        for report in history
                    ]
                }
            except Exception as e:
                logger.error(f"[WEB] Audit history error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.app.post("/api/image/analyze")
        async def analyze_image(file: UploadFile = File(...)):
            """Analyze an uploaded image."""
            image_analyzer = self.kernel.get_component('image_analyzer')
            if not image_analyzer:
                return {"error": "Image analyzer not available"}
            
            try:
                # Read image data
                image_data = await file.read()
                image_format = file.filename.split('.')[-1] if '.' in file.filename else 'png'
                
                # Analyze image
                result = await image_analyzer.analyze_image(image_data, image_format)
                
                return {
                    "success": True,
                    "description": result.description,
                    "classification": result.classification,
                    "ocr_text": result.ocr_text,
                    "metadata": result.metadata,
                    "analyzed_at": result.analyzed_at.isoformat()
                }
            except Exception as e:
                logger.error(f"[WEB] Image analysis error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.app.post("/api/agents/multi")
        async def dispatch_multi_agent(request: Dict[str, Any]):
            """Dispatch a task to multiple agents."""
            dispatcher = self.kernel.get_component('dispatcher')
            if not dispatcher:
                return {"error": "Dispatcher not available"}
            
            command = request.get("command", "")
            agents = request.get("agents", [])
            priority = request.get("priority", "medium")
            
            if not command or not agents:
                return {"error": "Command and agents list required"}
            
            try:
                from dispatcher.models import TaskPriority
                priority_map = {
                    "critical": TaskPriority.CRITICAL,
                    "high": TaskPriority.HIGH,
                    "medium": TaskPriority.MEDIUM,
                    "low": TaskPriority.LOW
                }
                
                task_id = await dispatcher.dispatch_multi_agent(
                    command=command,
                    agents=agents,
                    priority=priority_map.get(priority, TaskPriority.MEDIUM)
                )
                
                return {
                    "success": True,
                    "task_id": task_id,
                    "command": command,
                    "agents": agents,
                    "priority": priority
                }
            except Exception as e:
                logger.error(f"[WEB] Multi-agent dispatch error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.app.get("/api/dashboard/status")
        async def get_dashboard_status():
            """Get dashboard system status."""
            dashboard = self.kernel.get_component('dashboard')
            if not dashboard:
                return {"error": "Dashboard not available"}
            
            try:
                status = dashboard.get_system_status()
                return {
                    "success": True,
                    "status": status.to_dict()
                }
            except Exception as e:
                logger.error(f"[WEB] Dashboard status error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.app.post("/api/dashboard/mission")
        async def set_mission(request: Dict[str, Any]):
            """Set current mission."""
            dashboard = self.kernel.get_component('dashboard')
            if not dashboard:
                return {"error": "Dashboard not available"}
            
            try:
                dashboard.set_current_mission(
                    mission_id=request.get("mission_id", ""),
                    name=request.get("name", ""),
                    status=request.get("status", "in_progress"),
                    progress=request.get("progress", 0.0),
                    current_pr=request.get("current_pr")
                )
                
                return {"success": True}
            except Exception as e:
                logger.error(f"[WEB] Set mission error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.app.post("/api/dashboard/agent")
        async def update_agent_status(request: Dict[str, Any]):
            """Update agent status."""
            dashboard = self.kernel.get_component('dashboard')
            if not dashboard:
                return {"error": "Dashboard not available"}
            
            try:
                from dashboard.models import AgentStatus
                status_map = {
                    "idle": AgentStatus.IDLE,
                    "busy": AgentStatus.BUSY,
                    "error": AgentStatus.ERROR,
                    "disabled": AgentStatus.DISABLED
                }
                
                dashboard.update_agent_status(
                    name=request.get("name", ""),
                    status=status_map.get(request.get("status", "idle"), AgentStatus.IDLE),
                    current_task=request.get("current_task"),
                    tasks_completed=request.get("tasks_completed", 0)
                )
                
                return {"success": True}
            except Exception as e:
                logger.error(f"[WEB] Update agent status error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Send periodic updates
                    await asyncio.sleep(1)
                    
                    if self.kernel and self.kernel.context:
                        update = {
                            "type": "status_update",
                            "data": {
                                "state": self.kernel.state.value,
                                "command_count": self.kernel.context.command_count,
                                "error_count": self.kernel.context.error_count,
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                        await websocket.send_json(update)
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients."""
        for connection in self.websocket_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

    async def start(self):
        """Start the web server."""
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        logger.info(f"[WEB] Starting server at http://{self.host}:{self.port}")
        await server.serve()

    async def stop(self):
        """Stop the web server."""
        for connection in self.websocket_connections:
            await connection.close()
        self.websocket_connections.clear()
        logger.info("[WEB] Server stopped")
