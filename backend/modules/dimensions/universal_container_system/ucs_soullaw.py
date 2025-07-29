class SoulLawEnforcer:
    def validate_access(self, container: dict):
        if container.get("restricted", False):
            if container.get("access_key") != "GUARDIAN":
                raise PermissionError(f"🔒 SoulLaw: Access denied for {container['name']}")
        print(f"🔑 SoulLaw validated for {container.get('name')}")