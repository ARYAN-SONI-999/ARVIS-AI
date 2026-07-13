import inspect

class TaskRouter:
    def __init__(self):
        self.tools = {}
        self.register_tools()

    def register_tools(self):
        # Import skills here to avoid circular dependencies
        try:
            import skills.computer_control as cc
            self.tools["open_app"] = cc.open_app
            self.tools["close_app"] = cc.close_app
            self.tools["take_screenshot"] = cc.take_screenshot
            self.tools["type_text"] = cc.type_text
            self.tools["click_at"] = cc.click_at
            self.tools["press_keys"] = cc.press_keys
            self.tools["focus_window"] = cc.focus_window
        except ImportError as e:
            print(f"Warning: Failed to import computer control skills: {e}")

        try:
            import skills.file_manager as fm
            self.tools["list_files"] = fm.list_files
            self.tools["create_file"] = fm.create_file
            self.tools["delete_file"] = fm.delete_file
            self.tools["move_file"] = fm.move_file
            self.tools["search_files"] = fm.search_files
            self.tools["read_file"] = fm.read_file
        except ImportError as e:
            print(f"Warning: Failed to import file manager skills: {e}")

        try:
            import skills.web_search as ws
            self.tools["web_search"] = ws.web_search
        except ImportError as e:
            print(f"Warning: Failed to import web search skill: {e}")

        try:
            import skills.email_sender as es
            self.tools["send_email"] = es.send_email
        except ImportError as e:
            print(f"Warning: Failed to import email sender skill: {e}")

        try:
            import skills.code_executor as ce
            self.tools["execute_code"] = ce.execute_code
            self.tools["generate_code"] = ce.generate_code_draft
        except ImportError as e:
            print(f"Warning: Failed to import code executor skill: {e}")

        try:
            import skills.calculator as calc
            self.tools["evaluate_formula"] = calc.evaluate_formula
        except ImportError as e:
            print(f"Warning: Failed to import calculator skill: {e}")

        try:
            import skills.system_info as sysinfo
            self.tools["get_system_stats"] = sysinfo.get_system_stats
        except ImportError as e:
            print(f"Warning: Failed to import system info skill: {e}")

        try:
            import skills.scheduler as sched
            self.tools["schedule_task"] = sched.schedule_task
        except ImportError as e:
            print(f"Warning: Failed to import scheduler skill: {e}")

        try:
            import skills.system_control as sc
            self.tools["set_volume"]         = sc.set_volume
            self.tools["mute_volume"]        = sc.mute_volume
            self.tools["unmute_volume"]      = sc.unmute_volume
            self.tools["set_brightness"]     = sc.set_brightness
            self.tools["turn_on_wifi"]       = sc.turn_on_wifi
            self.tools["turn_off_wifi"]      = sc.turn_off_wifi
            self.tools["get_wifi_status"]    = sc.get_wifi_status
            self.tools["turn_on_bluetooth"]  = sc.turn_on_bluetooth
            self.tools["turn_off_bluetooth"] = sc.turn_off_bluetooth
            self.tools["lock_screen"]        = sc.lock_screen
            self.tools["sleep_system"]       = sc.sleep_system
            self.tools["shutdown_system"]    = sc.shutdown_system
            self.tools["restart_system"]     = sc.restart_system
            self.tools["cancel_shutdown"]    = sc.cancel_shutdown
            self.tools["get_battery_status"] = sc.get_battery_status
        except ImportError as e:
            print(f"Warning: Failed to import system control skill: {e}")

        try:
            import skills.news as nw
            self.tools["get_news"] = nw.get_news
        except ImportError as e:
            print(f"Warning: Failed to import news skill: {e}")

        try:
            import skills.file_manager as fm2
            if hasattr(fm2, 'search_in_file'):
                self.tools["search_in_file"] = fm2.search_in_file
        except Exception:
            pass

        try:
            import skills.web_reader as wr
            self.tools["browse_url"] = wr.browse_url
        except ImportError as e:
            print(f"Warning: Failed to import web reader skill: {e}")
        try:
            import skills.vision as vs2
            self.tools["analyze_screen"] = vs2.analyze_screen
        except ImportError as e:
            print(f"Warning: Failed to import vision skill: {e}")
        try:
            import skills.multi_agent as ma
            self.tools["delegate_task"] = ma.delegate_task
        except ImportError as e:
            print(f"Warning: Failed to import multi-agent skill: {e}")
    def route_call(self, tool_name, args):
        """Looks up the tool by name, validates arguments, and executes it.
        
        Returns a tuple: (success: bool, result_string: str)
        """
        if tool_name not in self.tools:
            return False, f"Error: Action '{tool_name}' is not supported or registered."

        tool_func = self.tools[tool_name]
        
        # Check function arguments matching
        try:
            sig = inspect.signature(tool_func)
            # Filter arguments to match the signature to prevent TypeError
            valid_args = {}
            for name, param in sig.parameters.items():
                if name in args:
                    valid_args[name] = args[name]
                elif param.default == inspect.Parameter.empty and param.kind not in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
                    # Missing required argument
                    return False, f"Error: Action '{tool_name}' is missing required argument '{name}'."
            
            # Execute tool
            if valid_args:
                result = tool_func(**valid_args)
            else:
                result = tool_func()
                
            return True, str(result)
            
        except Exception as e:
            return False, f"Error executing '{tool_name}': {str(e)}"
