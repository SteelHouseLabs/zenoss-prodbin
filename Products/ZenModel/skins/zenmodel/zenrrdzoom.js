/*
#####################################################
#
# ZenRRDZoom - Pan & Zoom for Zenoss RRDTool graphs
# 2006-12-29
#
#####################################################
*/

var zoom_factor = 1.5;
var pan_factor = 3; // Fraction of graph to move
var drange_re = /&drange=([0-9]*)/;
var end_re = /&end=now-([0-9]*)s/;
var width_re  = /&width=([0-9]*)/;
var height_re = /--height%3D([0-9]*)%7C/;
var start_re = /&start=end-([0-9]*)s/;
var comment_re = /&comment=.*$/;
var dashes_re = /(--.*?%7C)([^\-])/;

var linked_mode = 1;
var ZenQueue;

var Class={
    create:function(){
        return function(){
            this.__init__.apply(this,arguments);
        }
    }
}

Function.prototype.bind = function(obj) {
    var method = this;
    temp = function() {
        return method.apply(obj, arguments);
        };
    return temp;
}


Date.prototype.minus = function(secs) {
    return new Date(this.valueOf()-(secs*1000));
}
Date.prototype.toPretty = function() {
    return toISOTimestamp(this);
}


var table = function(obj, newme) {
    return "<table id='"+obj.id+"_table'"+
    "><tbody id='"+obj.id+"_tbody'></tbody></table>"
    /*
    return TABLE({'id':obj.id + '_table'},
    TBODY({'id':obj.id + '_tbody'}, 
    null));
    */
}
var firstrow = function(obj, newme) {
    _height = function(o) {
	return String(getElementDimensions(o).h + 14)+'px'; 
    };
    return TR({'style':'height:80px;'},[
    TD({'rowSpan':1,'style':'background:#ddd none;min-height:1%;'},
    INPUT({'type':'button',
    'id':obj.id + '_panl','style':'border:1px solid #aaa;width:3em;'+ 
    'cursor:pointer','value':'<', 'onfocus':'this.blur();'},null)),
    TD({'rowSpan':1}, newme),
    TD({'rowSpan':1, 'style':'background:#ddd none;' },
    INPUT({'type':'button',
    'id':obj.id + '_panr','style':'border:1px solid #aaa;'+
    'cursor:pointer;width:3em;','value':'>','onfocus':'this.blur();'},null)),
    TD({'style':'width:3em;'},
    DIV({'style':'width:3em;height:100%;min-height:164px;'},
    DIV({'id' : obj.id + '_zin','style':'cursor:pointer;background-color:#aaa;'+
    'width:3em;text-align:center;border:1px solid #aaa;vertical-align:middle;'+
    'background:#aaa url(zoomin.gif) center center no-repeat;height:50%;'+
    'min-height:82px;', 
    'valign':'middle'},''),
    DIV({'id':obj.id +'_zout','style':'cursor:pointer;background-color:#aaa;'+
    'width:3em;text-align:center;border:1px solid #aaa;height:50%;'+
    'background:transparent url(zoomout.gif) center center no-repeat;'+
    'min-height:82px;', 
    'valign':'middle'}, '')))]);
}

ZenRRDGraph = Class.create();
ZenRRDGraph.prototype = {

    zoom_factor: 1.5,
    pan_factor: 3,

    __init__: function(obj) {
        this.obj = obj;
        this.updateFromUrl();
        this.setDates();
        this.buildTables();
        this.registerListeners();
        this.loadImage();
    },

    updateFromUrl: function() {
        var href = this.obj.src;
        this.drange = Number(drange_re.exec(href)[1]);
        this.width  = Number(width_re.exec(href)[1]);
        this.end    = Number(end_re.exec(href)?end_re.exec(href)[1]:0);
        this.start  = Number(start_re.exec(href)?start_re.exec(href)[1]
                             :this.drange);
    },

    imgPos: function() {
        obj = this.obj;
        var curleft = curtop = 0;
        if (obj.offsetParent) {
            curleft = obj.offsetLeft;
            curtop = obj.offsetTop;
            while (obj=obj.offsetParent) {
                curleft += obj.offsetLeft;
                curtop += obj.offsetTop;
            }
        }
        var element = {x:curleft,y:curtop};
        return element;
    },

    setxpos: function(e) {
        e = e || window.event;
        var cursor = {x:0,y:0};
        var element = this.imgPos();
        if (e.pageX || e.pageY) {
            cursor.x = e.pageX;
            cursor.y = e.pageY;
        } else {
            var de = document.documentElement;
            var b = document.body;
            cursor.x = e.mouse().client.x +
                (de.scrollLeft||b.scrollLeft)-(de.clientLeft||0);
            cursor.y = e.mouse().client.y +
                (de.scrollTop||b.scrollTop)-(de.clientTop||0);
        }
        return cursor.x - element.x;
    },

    startString : function(s) {
        s = s || this.start;
        var x = "&start=end-" + String(s) + "s";
        return x;
    },

    endString : function(e) {
        e = e || this.end;
        var x = "&end=now-" + String(e) + "s";
        return x;
    },

    setZoom : function(e) {
        var x = this.setxpos(e)-67;
        var href = this.obj.src;
        if (x<0||x>this.width){return href};
        var drange = Math.round(this.drange/this.zoom_factor);
        var delta = ((this.width/2)-x)*(this.drange/this.width) +
                (this.drange-drange)/2;
        var end = Math.round(this.end+delta>=0?this.end+delta:0);
        this.drange = drange;
        this.start = drange;
        this.end = end;
        return [this.drange, this.start, this.end];
    },

    pan_left : function() {
        var delta = Math.round(this.drange/this.pan_factor);
        this.end = this.end+delta>0?this.end+delta:0;
        this.setDates();
        this.setComment();
        this.setUrl();
        this.loadImage();
    },

    pan_right : function() {
        var delta = Math.round(this.drange/this.pan_factor);
        this.end = this.end-delta>0?this.end-delta:0;
        this.setDates();
        this.setComment();
        this.setUrl();
        this.loadImage();
    },

    setDates : function() {
        var sD, eD;
        now = new Date();
        eD = now.minus(this.end); 
        sD = now.minus(this.start+this.end);
        this.sDate=sD.toPretty();
        this.eDate=eD.toPretty();
        delete now;
    },

    setComment : function(comment) {
        var com_ctr = "\\t\\t\\t\\t to \\t\\t\\t";
        comment = comment || this.sDate + com_ctr + this.eDate;
        comment = comment.replace(/:/g, '\\:');
        //this.comment = escape("COMMENT:" + comment + "\\c|");
        this.comment = escape(comment);
    },
    
    setUrl : function() {
        var newurl, dashes;
        var href = this.obj.src;
        var start_url = this.startString();
        var end_url = this.endString();
        if ( href.match(end_re) ) {
            newurl = href.replace(end_re, end_url);
            newurl = newurl.replace(start_re, start_url);
        } else {
            newurl = href+=start_url+end_url;
        };
        newurl = newurl.replace(drange_re, "&drange=" + String(this.drange));
        this.setDates();
        this.setComment();
        if (newurl.match(comment_re)) {
            newurl = newurl.replace(comment_re, "&comment=" + this.comment);
        } else {
            newurl = newurl + "&comment=" + this.comment;
        }
        this.url = newurl;
    },

    doZoom : function(e) {
        this.setZoom(e);
        this.setDates();
        this.setComment();
        this.setUrl();
        this.loadImage();
    },
    
    buildTables : function() {
        this.setComment();
        this.setUrl();
        var newme = this.obj.cloneNode(false);
        newme.src = this.url;
        newme.style.cursor = 'crosshair';
        var t = table(this.obj, newme);
        var f = firstrow(this.obj, newme);
        var old = this.obj.parentNode.innerHTML;
        var objid = this.obj.id;
        this.obj.parentNode.innerHTML = old+t;
        this.obj = $(objid);
        var tb = $(this.obj.id + '_tbody');
        tb.appendChild(f);
        this.obj.parentNode.removeChild(this.obj);
        this.obj = newme;
        this.zin = $(this.obj.id + '_zin');
        this.zout = $(this.obj.id + '_zout');
        this.panl = $(this.obj.id + '_panl');
        this.panr = $(this.obj.id + '_panr');
    },

    zoom_in : function() {
        setStyle(this.zin, {'background':'#aaa url(zoomin.gif) center center no-repeat'});
        setStyle(this.zout, {'background':'transparent url(zoomout.gif) center center no-repeat'});
        if (this.zoom_factor < 1) this.zoom_factor=1/this.zoom_factor;
    },

    zoom_out: function() {
        setStyle(this.zin, {'background':'transparent url(zoomin.gif) center center no-repeat'});
        setStyle(this.zout, {'background':'#aaa url(zoomout.gif) center center no-repeat'});
        if (this.zoom_factor > 1) this.zoom_factor=1/this.zoom_factor;
    },

    loadImage : function() {
        checkurl = this.url+'&getImage=';
        var onSuccess = bind(function(r) {
            if (r.responseText=='True') {
                if (this.obj.src!=this.url) {
                    this.obj.src = this.url;
                };
            }
        }, this);
        var setHeights = bind(function(e) {
            var myh = getElementDimensions(this.obj).h;
            setElementDimensions(this.panl, {'h':myh});
            setElementDimensions(this.panr, {'h':myh});
        }, this);
        var x = connect(this.obj, 'onload', setHeights);
        if (this.url!=this.obj.src) {
            defr = doXHR(checkurl)
            defr.addCallback(onSuccess)
        }
    },

    registerListeners : function() {
        if (!this.listeners) this.listeners=new Array();
        this.clearListeners();
        var l = this.listeners;
        l[0] = connect(this.obj, 'onclick', this.doZoom.bind(this));
        l[1] = connect(this.zin, 'onclick', this.zoom_in.bind(this));
        l[2] = connect(this.zout,'onclick', this.zoom_out.bind(this));
        l[3] = connect(this.panl,'onclick', this.pan_left.bind(this));
        l[4] = connect(this.panr,'onclick', this.pan_right.bind(this));
    },

    clearListeners : function() {
        for (l=0;l<this.listeners.length;l++){
            disconnect(this.listeners[l]);
        }
    }

}

ZenGraphQueue = Class.create();

ZenGraphQueue.prototype = {
    graphs : [],
    __init__: function() {
        for (var g=0; g<this.graphs.length; g++) {
            graph = this.graphs[g];
            this.add.bind(this)(graph);
        }
    },
    add: function(graph) {
        this.graphs[this.graphs.length] = graph;
        this.registerListeners(graph);
    },
    reset: function(graph) {
        for (g=0; g<graphs.length; g++) {
            this.registerListeners(this.graphs[g]);
        }
    },
    registerListeners: function(graph) {
        if (!graph.listeners) graph.listeners=new Array();
        var l = graph.listeners;
        graph.clearListeners();
        l[0] = connect(graph.obj, 'onclick', this.doZoom.bind(this));
        l[1] = connect(graph.zin, 'onclick', this.zoom_in.bind(this));
        l[2] = connect(graph.zout,'onclick', this.zoom_out.bind(this));
        l[3] = connect(graph.panl,'onclick', this.pan_left.bind(this));
        l[4] = connect(graph.panr,'onclick', this.pan_right.bind(this));
    },
    remove: function(graph) {
        graph.registerListeners();
    },
    removeAll: function() {
        for (g=0; g<this.graphs.length; g++) {
            this.remove(this.graphs[g]);
        }
    },
    updateAll: function(vars) {
        var end = vars[2];
        var start = vars[1];
        var drange = vars[0];
        for (var i=0; i<this.graphs.length; i++) {
            var x = this.graphs[i];
            var blah;
            x.end = end;
            x.start = start;
            x.drange = drange;
            x.setDates();
            x.setComment();
            x.setUrl();
            x.loadImage();
        }
    },
    doZoom: function(e) {
        var g = this.find_graph(e.target());
        var graph = this.graphs[g];
        var vars = graph.setZoom.bind(graph)(e);
        this.updateAll(vars);
    },
    zoom_in: function(e) {
        for (g=0; g<this.graphs.length; g++) {
            graph = this.graphs[g];
            bind(graph.zoom_in, graph)(e);
        }
    },
    zoom_out: function(e) {
        for (g=0; g<this.graphs.length; g++) {
            graph = this.graphs[g];
            graph.zoom_out.bind(graph)(e);
        }
    },
    pan_left: function(e) {
        for (g=0; g<this.graphs.length; g++) {
            graph = this.graphs[g];
            graph.pan_left.bind(graph)(e);
        }
    },
    pan_right: function(e) {
        for (g=0; g<this.graphs.length; g++) {
            graph = this.graphs[g];
            graph.pan_right.bind(graph)(e);
        }
    },
    find_graph: function(obj) {
        for (g=0; g<this.graphs.length; g++) {
            if (this.graphs[g].obj==obj) return g;
        }
    }
};

function linkGraphs(bool) {
    linked_mode = bool;
    if (!linked_mode) {
        ZenQueue.removeAll();
    } else {
        resetGraphs($('drange_select').value);
        ZenQueue.reset();
    }
}

function resetGraphs(drange) {
    var end = 0;
    var start = Number(drange);
    var drange = Number(drange);
    ZenQueue.updateAll([drange, start, end]);
}

function registerGraph(id) {
    var graph = new ZenRRDGraph($(id));
}

function zenRRDInit() {
    ZenQueue = new ZenGraphQueue();
    for (var graphid=0; graphid<ZenGraphs.length; graphid++) {
        try {
            graph = new ZenRRDGraph($(ZenGraphs[graphid]));
            ZenQueue.add(graph);
        } catch(e) { 
           mydiv = DIV({'style':'height:100px;width:300px;'},
            "There was a problem rendering this graph. If you've just added "+
            'this device, template or datapoint, please wait half an hour for data to be collected.');
           swapDOM($(ZenGraphs[graphid]), mydiv);
        }
    }
}

addLoadEvent(zenRRDInit);
