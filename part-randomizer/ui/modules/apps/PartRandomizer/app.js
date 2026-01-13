angular.module("beamng.apps").directive("partRandomizer", function () {
  return {
    restrict: "E",
    templateUrl: "/ui/modules/apps/PartRandomizer/app.html",
    replace: true,
    controller: function ($scope) {
      $scope.randomize = function () {
        if (window.bngApi && window.bngApi.engineLua) {
          window.bngApi.engineLua("extensions.part_randomizer.requestRandomTuning()");
        }
      };
    },
  };
});
