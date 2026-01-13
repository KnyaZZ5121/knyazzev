local M = {}

local function seedRandom()
  math.randomseed(os.time() + math.floor((os.clock() % 1) * 100000))
  math.random()
end

local function getPlayerVehicle()
  if be == nil or be.getPlayerVehicle == nil then
    return nil
  end
  return be:getPlayerVehicle(0)
end

local function pickRandomPart(parts)
  if type(parts) ~= "table" or #parts == 0 then
    return nil
  end
  return parts[math.random(#parts)]
end

local function buildRandomConfig(available)
  local config = {}
  for slot, parts in pairs(available) do
    local choice = pickRandomPart(parts)
    if choice ~= nil then
      config[slot] = choice
    end
  end
  return config
end

local function applyRandomConfig(vehicle)
  local partmgmt = extensions and extensions.core_vehicle_partmgmt or nil
  if not partmgmt or not partmgmt.getAvailableParts or not partmgmt.setConfig then
    return
  end

  local available = partmgmt.getAvailableParts(vehicle) or {}
  local randomConfig = buildRandomConfig(available)
  if next(randomConfig) == nil then
    return
  end

  partmgmt.setConfig(vehicle, randomConfig)
end

local function randomizeTuningValues(vehicle)
  local tuning = extensions and extensions.core_vehicle_tuning or nil
  if not tuning or not tuning.getTunableVars or not tuning.setTuningVars then
    return
  end

  local vars = tuning.getTunableVars(vehicle) or {}
  local newVars = {}

  for name, data in pairs(vars) do
    if type(data) == "table" and data.min ~= nil and data.max ~= nil then
      local minValue = tonumber(data.min) or 0
      local maxValue = tonumber(data.max) or 0
      local value = minValue + math.random() * (maxValue - minValue)
      if data.step then
        local step = tonumber(data.step) or 0
        if step > 0 then
          value = minValue + math.floor((value - minValue) / step + 0.5) * step
        end
      end
      newVars[name] = value
    end
  end

  if next(newVars) ~= nil then
    tuning.setTuningVars(vehicle, newVars)
  end
end

local function randomizeVehicle()
  local vehicle = getPlayerVehicle()
  if not vehicle then
    return
  end

  applyRandomConfig(vehicle)
  randomizeTuningValues(vehicle)
end

function M.requestRandomTuning()
  randomizeVehicle()
end

function M.onInit()
  seedRandom()
end

return M
