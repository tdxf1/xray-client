import flet as ft
from backendflet import XrayBackend
import threading
import os

class XrayClientUI:
    def __init__(self, page: ft.Page):
        self.page = page
        self.backend = XrayBackend()
        self.page.title = "XC (Xray-Client)"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 20
        self.selected_config = None  # Property to store the selected config
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[ft.Tab(text="Home")],
            expand=1,
        )
        self.create_ui()

    def create_ui(self):
        # Create Home tab content
        system_info = self.backend.get_system_info()
        
        info_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"XC (Xray-Client)", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Version: {self.backend.version}", size=16),
                    ft.Divider(),
                    *[ft.Text(f"{key}: {value}", size=14) for key, value in system_info.items()],
                ]),
                padding=20,
            ),
            elevation=5,
        )

        self.xray_button = ft.ElevatedButton(
            "Start Xray",
            on_click=self.toggle_xray,
            style=ft.ButtonStyle(
                color={
                    ft.ControlState.DEFAULT: ft.colors.WHITE,
                    ft.ControlState.HOVERED: ft.colors.WHITE,
                },
                bgcolor={
                    ft.ControlState.DEFAULT: ft.colors.BLUE,
                    ft.ControlState.HOVERED: ft.colors.BLUE_700,
                },
            )
        )
        
        self.log_view = ft.TextField(
            multiline=True,
            read_only=True,
            expand=True,
            min_lines=10,
            max_lines=20,
            border_color=ft.colors.BLUE_200,
        )

        home_content = ft.Column([
            info_card,
            ft.Container(height=20),
            self.xray_button,
            ft.Container(height=20),
            ft.Text("Xray Logs:", size=18, weight=ft.FontWeight.BOLD),
            self.log_view
        ], expand=True, spacing=10)

        self.tabs.tabs[0].content = home_content

        # Create tabs for each profile
        for profile in self.backend.get_profiles():
            self.add_profile_tab(profile)

        # Add import button
        import_button = ft.ElevatedButton(
            "Import Subscription",
            on_click=self.show_import_dialog,
            style=ft.ButtonStyle(
                color={
                    ft.ControlState.DEFAULT: ft.colors.WHITE,
                    ft.ControlState.HOVERED: ft.colors.WHITE,
                },
                bgcolor={
                    ft.ControlState.DEFAULT: ft.colors.GREEN,
                    ft.ControlState.HOVERED: ft.colors.GREEN_700,
                },
            )
        )

        self.page.add(import_button, self.tabs)

    def add_profile_tab(self, profile):
        configs = self.backend.get_configs(profile)

        # Use ListView for scrolling
        config_list = ft.ListView(expand=1, spacing=0, padding=20)

        for config in configs:
            is_selected = config == self.selected_config
            config_list.controls.append(
                ft.ListTile(  # Use ListTile to display config
                    title=ft.Container(  # Use Container to change background color
                        content=ft.Text(config),
                        bgcolor=ft.colors.BLACK87 if is_selected else ft.colors.TRANSPARENT,  # Change color based on selection
                        padding=ft.padding.all(8)  # Set internal padding
                    ),
                    on_click=lambda e, config=config: self.select_config(config, profile),  # Select config
                )
            )

        update_button = ft.ElevatedButton("Update", on_click=lambda _: self.update_subscription(profile))
        delete_button = ft.ElevatedButton("Delete", on_click=lambda _: self.delete_subscription(profile))
        ping_all_button = ft.ElevatedButton("Ping All", on_click=lambda _: self.ping_all_configs(profile, config_list))

        tab_content = ft.Column([
            ft.Row([update_button, delete_button, ping_all_button]),
            config_list
        ], expand=True)

        self.tabs.tabs.append(ft.Tab(
            text=profile,
            content=tab_content
        ))
        self.page.update()

    def select_config(self, config, profile):
        self.selected_config = config  # Store the selected config
        print(f"Selected config: {config}")  # Print the name of the selected config
        self.refresh_profile_tab(profile)  # Refresh the appearance of configs

    def refresh_profile_tab(self, profile):
        for tab in self.tabs.tabs:
            if tab.text == profile:
                configs = self.backend.get_configs(profile)
                config_list = tab.content.controls[1]
                config_list.controls.clear()
                for config in configs:
                    is_selected = config == self.selected_config
                    config_list.controls.append(
                        ft.ListTile(
                            title=ft.Container(
                                content=ft.Text(config),
                                bgcolor=ft.colors.BLACK87 if is_selected else ft.colors.TRANSPARENT,
                                padding=ft.padding.all(8)
                            ),
                            on_click=lambda e, config=config: self.select_config(config, profile),
                        )
                    )
                break
        self.page.update()

    def update_subscription(self, profile):
        self.backend.update_subscription(profile)
        self.refresh_profile_tab(profile)

    def delete_subscription(self, profile):
        self.backend.delete_subscription(profile)
        for i, tab in enumerate(self.tabs.tabs):
            if tab.text == profile:
                self.tabs.tabs.pop(i)
                break
        self.page.update()

    def ping_all_configs(self, profile, config_list):
        def ping_worker():
            for control in config_list.controls:
                config_name = control.title.content.value
                config_num = config_name.split("-")[0].strip()
                result = self.backend.ping_config(profile, config_num)
                control.title.content = ft.Text(f"{config_name} (Ping: {result})")
            self.page.update()

        threading.Thread(target=ping_worker, daemon=True).start()

    def show_import_dialog(self, e):
        def import_sub(e):
            name = name_field.value
            url = url_field.value
            if name and url:
                self.backend.import_subscription(name, url)
                self.add_profile_tab(name)
                dialog.open = False
                self.page.update()

        name_field = ft.TextField(label="Profile Name")
        url_field = ft.TextField(label="URL")
        dialog = ft.AlertDialog(
            title=ft.Text("Import Subscription"),
            content=ft.Column([name_field, url_field], tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self.close_dialog(dialog)),
                ft.TextButton("Import", on_click=import_sub),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()


    def toggle_xray(self, e):
        if self.backend.xray_process is None:
            config_path = f"./core/{self.backend.os_sys}/select.txt"
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    selected_config = f.read().strip()
                message = self.backend.run_xray(selected_config)
                self.xray_button.text = "Stop Xray"
                self.xray_button.style.bgcolor = {
                    ft.ControlState.DEFAULT: ft.colors.RED,
                    ft.ControlState.HOVERED: ft.colors.RED_700,
                }
                self.log(message)
                threading.Thread(target=self.read_xray_logs, daemon=True).start()
            else:
                self.log("No config selected. Please select a config first.")
        else:
            message = self.backend.stop_xray()
            self.xray_button.text = "Start Xray"
            self.xray_button.style.bgcolor = {
                ft.ControlState.DEFAULT: ft.colors.BLUE,
                ft.ControlState.HOVERED: ft.colors.BLUE_700,
            }
            self.log(message)
        self.page.update()

    def read_xray_logs(self):
        for log_line in self.backend.read_xray_logs():
            self.log(log_line)

    def log(self, message):
        self.log_view.value += f"{message}\n"
        self.page.update()

def main(page: ft.Page):
    XrayClientUI(page)

ft.app(target=main)
