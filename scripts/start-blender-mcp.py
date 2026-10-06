"""Launch with blender --python scripts/start-blender-mcp.py."""
import bpy
import addon_utils
addon_utils.enable('blender_mcp', default_set=True, persistent=True)
import blender_mcp
bpy.ops.wm.save_userpref()
# Registration starts the add-on's loopback server automatically.
