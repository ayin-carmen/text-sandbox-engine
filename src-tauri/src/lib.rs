use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::{Manager, RunEvent};

struct ApiProcess(Mutex<Option<Child>>);

pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let child = Command::new("python")
                .args(["-m", "text_sandbox_editor_api"])
                .spawn()
                .ok();
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
