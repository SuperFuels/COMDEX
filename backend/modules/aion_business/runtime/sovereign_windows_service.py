"""Windows Service Control Manager adapter for the loopback-only installed brain service."""

from __future__ import annotations

try:  # Imported only on Windows packages containing pywin32.
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
except ImportError:  # Permit packaging and source inspection on other platforms.
    servicemanager = win32event = win32service = win32serviceutil = None

from backend.modules.aion_business.runtime.sovereign_installed_service import (
    create_health_server,
    default_brain_root,
    default_health_endpoint_path,
    remove_endpoint_record,
)


if win32serviceutil is not None:
    class PilotBrainWindowsService(win32serviceutil.ServiceFramework):
        _svc_name_ = "TessarisPilotBrain"
        _svc_display_name_ = "Tessaris Pilot AION Brain"
        _svc_description_ = "Local, customer-controlled AION brain health service."

        def __init__(self, args):
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.server, self.endpoint, self.endpoint_path = create_health_server(
                root=default_brain_root(),
                host="127.0.0.1",
                port=0,
                endpoint_path=default_health_endpoint_path(),
            )

        def SvcStop(self):  # noqa: N802
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.server.shutdown()
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):  # noqa: N802
            servicemanager.LogInfoMsg("Tessaris Pilot AION Brain service started")
            try:
                self.server.serve_forever()
            finally:
                self.server.server_close()
                remove_endpoint_record(
                    self.endpoint_path,
                    instance_id=str(self.endpoint["instance_id"]),
                )


def main() -> int:
    if win32serviceutil is None:
        raise RuntimeError("The Windows service adapter requires pywin32 on Windows")
    win32serviceutil.HandleCommandLine(PilotBrainWindowsService)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
