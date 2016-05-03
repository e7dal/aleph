
aleph.factory('Authz', ['$rootScope', function($rootScope) {
  var checkCollection = function(right, collection_id) {
    if ($rootScope.session.permissions.collections && $rootScope.session.permissions.collections[right]) {
        return $rootScope.session.permissions.collections[right].indexOf(collection_id) != -1;
      }
      return false;
  }

  var checkSource = function(right, source_id) {
    if ($rootScope.session.permissions.sources && $rootScope.session.permissions.sources[right]) {
      return $rootScope.session.permissions.sources[right].indexOf(source_id) != -1;
    }
    return false;
  }

  return {
    collection: checkCollection,
    source: checkSource,
    READ: 'read',
    WRITE: 'write'
  }
}]);
