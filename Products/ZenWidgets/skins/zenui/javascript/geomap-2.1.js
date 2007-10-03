var Class = YAHOO.zenoss.Class;

function ZenossLocationCache() {
    GGeocodeCache.apply(this);
}

ZenossLocationCache.prototype = new GGeocodeCache();
ZenossLocationCache.prototype.reset = function() {
    GGeocodeCache.prototype.reset.call(this);
    if (geocodecache) {
      var mycache = geocodecache.v;
    } else {
      var mycache = [];
    }
    for (var i in mycache) { 
        this.put(mycache[i].name, mycache[i]);
    }
}

var ZenGeoMap = Class.create();
ZenGeoMap.prototype = {
    __init__: function(container){
        this.lock = new DeferredLock();
        this.map = new GMap2(container);
        this.map.addControl(new GSmallMapControl());
        this.map.setCenter(new GLatLng(0,0),0);
        this.bounds = new GLatLngBounds();
        this.cache = new ZenossLocationCache();
        this.dirtycache = false;
        this.geocoder = new GClientGeocoder(this.cache);
        var icon = new GIcon();
        icon.iconSize = new GSize(18,18);
        icon.iconAnchor = new GPoint(9,9);
        this.baseIcon = icon;
        bindMethods(this);
    },
    showAllMarkers: function(){
        var d = this.lock.acquire();
        d.addCallback(bind(function(){
        this.map.setZoom(this.map.getBoundsZoomLevel(this.bounds));
        this.map.setCenter(this.bounds.getCenter());
        this.lock.release();
        }, this));
    },
    Dot: function(p, color) {
        var icon = new GIcon(this.baseIcon);
        icon.image = "img/"+color+"_dot.png";
        return new GMarker(p, icon);
    },
    addPolyline: function(addresses) {
        var addys = addresses[0];
        var severity = addresses[1];
        var color = severity>0?'#ff0000':'#00ff00';
        var points = []
        var lock = new DeferredLock();
        var lock2 = new DeferredLock();
        var addadd = bind(function(address) {
            var d = lock.acquire();
            d.addCallback(bind(function(p){
                this.geocoder.getLatLng(
                address,
                function(p){
                    points.push(p);
                    if(points.length==addys.length){
                        if (lock2.locked) lock2.release();
                    }
                    lock.release();
                });
            }, this));
        }, this);
        var e = lock2.acquire();
        e.addCallback(bind(function(){
            map(addadd, addys);
        }, this));
        var f = lock2.acquire();
        f.addCallback(bind(function(p){
            var polyline = new GPolyline(points, color, 3);
            this.map.addOverlay(polyline);
            lock2.release();
        }, this));
    },
    addMarker: function(address, color, clicklink, summarytext){
        var d = this.lock.acquire();
        d.addCallback(bind(function(){
        if (this.cache.get(address)==null) this.dirtycache = true;
        clicklink = clicklink.replace('locationGeoMap', 'simpleLocationGeoMap');
        this.geocoder.getLatLng(
            address,
            bind(function(p){
                if (!p) {
                    noop()
                } else {
                    var marker = this.Dot(p, color);
                    GEvent.addListener(marker, "click", function(){
                        if (clicklink.search('ocationGeoMap')>0){
                           location.href = clicklink;
                        } else {
                            currentWindow().parent.location.href = clicklink
                        }

                       });
                    this.map.addOverlay(marker);
                    var markerimg = marker.Oj
                    /*
                    Ext.QuickTips.register({
                        target: markerimg,
                        title: address,
                        text: summarytext
                    });
                    */
                    this.bounds.extend(p);
                    this.lock.release();
                }
            }, this)
        )}, this));
    },
    saveCache: function() {
        if (this.dirtycache) {
            cachestr = serializeJSON(this.cache);
            savereq = doXHR( 
                '/zport/dmd/setGeocodeCache', 
                {'sendContent':cachestr,
                 'method':'POST',
                 'mimeType':'text/plain'
                }
            );
        }
        this.dirtycache = false;
        this.lock.release();
    },
    doDraw: function(results) {
        var x = this;
        var nodedata = results.nodedata;
        var linkdata = results.linkdata;
        var secondarynodedata = results.secondarynodedata;
        this.map.clearOverlays();
        for (i=0;i<nodedata.length;i++) {
            var node = nodedata[i];
            if (node[0].length>0) 
                x.addMarker(node[0], node[1], node[2], node[3]);
        }
        x.showAllMarkers();
        for (i=0;i<secondarynodedata.length;i++) {
            var node = secondarynodedata[i];
            if (node[0].length>0) 
                x.addMarker(node[0], node[1], node[2], node[3]);
        }
        for (j=0;j<linkdata.length;j++) {
            x.addPolyline(linkdata[j]);
        }
        d = x.lock.acquire();
        d.addCallback(x.saveCache);
    },
    refresh: function() {
        var results = {
            'nodedata':[],
            'linkdata':[],
            'secondarynodedata':[]
        };
        var myd = loadJSONDoc('getChildGeomapData');
        myd.addCallback(function(x){results['nodedata'] = x});
        var myd2 = loadJSONDoc('getChildLinks');
        myd2.addCallback(function(x){results['linkdata'] = x});
        var myd3 = loadJSONDoc('getSecondaryNodes');
        myd3.addCallback(function(x){results['secondarynodedata'] = x});
        var bigd = new DeferredList([myd, myd2, myd3], false, false, true);
        bigd.addCallback(method(this, function(){this.doDraw(results)}));
    }
}

function geomap_initialize(){
    var x = new ZenGeoMap($('geomapcontainer'));
    connect(currentWindow(), 'onunload', GUnload);
    var portlet_id = currentWindow().frameElement.parentNode.id.replace(
        '_body', '');
    var pobj = currentWindow().parent.ContainerObject.portlets[portlet_id];
    pobj.mapobject = x;
    x.refresh();
}

addLoadEvent(geomap_initialize);
