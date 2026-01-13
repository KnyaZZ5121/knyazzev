(function () {
  "use strict";

  angular.module("beamng.apps").controller("randomTuningController", function () {
    const vm = this;

    vm.randomize = function () {
      if (window.beamng && window.beamng.sendEngineLua) {
        window.beamng.sendEngineLua("extensions.random_tuning.randomize()")
      }
    };
  });
})();
