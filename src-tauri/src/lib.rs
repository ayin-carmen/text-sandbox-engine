use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::{Manager, RunEvent};

struct ApiProcess(Mutex<Option<Child>>);

pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let packaged_api = app
                .path()
                .resource_dir()
                .ok()
                .map(|path| path.join("text-sandbox-editor-api.exe"));
            let child = match packaged_api.filter(|path| path.exists()) {
                Some(path) => Command::new(path).spawn().ok(),
                None => Command::new("python")
                    .args(["-m", "text_sandbox_editor_api"])
                    .spawn()
                    .ok(),
            };
            app.manage(ApiProcess(Mutex::new(child)));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let RunEvent::Exit = event {
                if let Some(process) = app_handle.try_state::<ApiProcess>() {
                    if let Ok(mut child) = process.0.lock() {
                        if let Some(child) = child.as_mut() {
                            let _ = child.kill();
                        }
                    }
                }
            }
        });
}
