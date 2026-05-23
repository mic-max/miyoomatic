-- mGBA Lua script: watches a trigger file each frame; when it appears, reads the
-- destination path from it, calls emu:screenshot(path), then deletes the trigger.
-- Load via mGBA: Tools -> Scripting -> File -> Load script... (then point at this file).
-- mGBA must be running a ROM and not paused for frame callbacks to fire.

local TRIGGER_PATH = "C:/Git/miyoomatic/tmp/shot.trigger"

local function tick()
    local f = io.open(TRIGGER_PATH, "r")
    if not f then return end
    local out = f:read("*l")
    f:close()
    os.remove(TRIGGER_PATH)
    if out and #out > 0 then
        emu:screenshot(out)
    end
end

callbacks:add("frame", tick)
