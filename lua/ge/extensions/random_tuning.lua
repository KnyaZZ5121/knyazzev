local M = {}

local function getPlayerVehicle()
  local veh = be:getPlayerVehicle(0)
  if not veh then
    log("W", "random_tuning", "No active player vehicle found")
    return nil
  end
  return veh
end

local function randomize()
  local veh = getPlayerVehicle()
  if not veh then
    return
  end

  veh:queueLuaCommand("extensions.random_tuning.randomize()")
end

M.randomize = randomize

return M
