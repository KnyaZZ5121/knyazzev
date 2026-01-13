local M = {}

local function getRandomChoice(choices)
  if not choices then
    return nil
  end

  local list = {}
  for name, _ in pairs(choices) do
    table.insert(list, name)
  end

  if #list == 0 then
    return nil
  end

  return list[math.random(#list)]
end

local function applyRandomParts(config)
  local slotMap = v.data and v.data.slotMap or {}
  for slotName, slotData in pairs(slotMap) do
    if slotData and slotData.choices then
      local choice = getRandomChoice(slotData.choices)
      if choice then
        config[slotName] = choice
      end
    end
  end
end

local function clamp(val, minVal, maxVal)
  if val < minVal then
    return minVal
  end
  if val > maxVal then
    return maxVal
  end
  return val
end

local function randomizeVars(config)
  config.vars = config.vars or {}
  local variables = v.data and v.data.variables or {}

  for varName, varData in pairs(variables) do
    if type(varData) == "table" and varData.min ~= nil and varData.max ~= nil then
      local minVal = tonumber(varData.min) or 0
      local maxVal = tonumber(varData.max) or minVal
      if minVal > maxVal then
        minVal, maxVal = maxVal, minVal
      end

      local value = minVal + math.random() * (maxVal - minVal)
      if varData.step then
        local step = tonumber(varData.step) or 0
        if step > 0 then
          value = math.floor(value / step + 0.5) * step
        end
      end

      config.vars[varName] = clamp(value, minVal, maxVal)
    end
  end
end

local function randomize()
  local config = v.config or {}
  local newConfig = {}

  for key, value in pairs(config) do
    newConfig[key] = value
  end

  applyRandomParts(newConfig)
  randomizeVars(newConfig)

  if extensions.partmgmt and extensions.partmgmt.setConfig then
    extensions.partmgmt.setConfig(newConfig)
  else
    log("W", "random_tuning", "partmgmt.setConfig not available; cannot apply randomized parts")
  end
end

M.randomize = randomize

return M
