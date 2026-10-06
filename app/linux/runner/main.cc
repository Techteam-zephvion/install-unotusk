#include "my_application.h"
#include <stdlib.h>
#include <string.h>

int main(int argc, char** argv) {
  // Prefer X11/XWayland backend to avoid GTK/Wayland EGL subsurface frame timeout
  // and viewport desynchronization artifacts on Wayland compositors (Hyprland, Mutter, KWin).
  const char* gdk_backend = getenv("GDK_BACKEND");
  if (gdk_backend == nullptr || strcmp(gdk_backend, "wayland") == 0) {
    setenv("GDK_BACKEND", "x11,wayland", 1);
  }

  g_autoptr(MyApplication) app = my_application_new();
  return g_application_run(G_APPLICATION(app), argc, argv);
}
