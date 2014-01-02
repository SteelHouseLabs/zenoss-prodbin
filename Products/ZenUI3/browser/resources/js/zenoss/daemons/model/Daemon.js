/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    var monitorRouter = Zenoss.remote.MonitorRouter;
    var appRouter = Zenoss.remote.ApplicationRouter;

    Ext.define('Daemons.model.Collector', {
        extend: 'Ext.data.Model',
        fields: Zenoss.model.BASE_TREE_FIELDS.concat([
            {name: 'id',  type: 'string'},
            {name: 'name',  type: 'string'},
            {name: 'uid',  type: 'string'},
            {name: 'uuid',  type: 'string'},
        ]),
        proxy: {
            simpleSortMode: true,
            type: 'direct',
            directFn: monitorRouter.getTree,
            paramOrder: ['uid']
        }
    });

    Ext.define('Daemons.store.Collectors', {
        extend: 'Ext.data.TreeStore',
        model: 'Daemons.model.Collector',
        nodeParam: 'uid',
        remoteSort: false,
        sorters: {
            direction: 'asc',
            sorterFn: Zenoss.sortTreeNodes
        }
    });

    Ext.define('Daemons.model.Daemon', {
        extend: 'Ext.data.Model',
        fields: Zenoss.model.BASE_TREE_FIELDS.concat([
            {name: 'id',  type: 'string'},
            {name: 'name',  type: 'string'},
            {name: 'uid',  type: 'string'},
            {name: 'uuid',  type: 'string'},
            {name: 'state',  type: 'string',
             convert: function(value, record) {
                 return Daemons.states[value] || value;
             }
            },
            {name: 'uptime', type: 'string'},
            {name: 'autostart',  type: 'boolean'},
            {name: 'isRestarting',  type: 'boolean'},
            {name: 'qtip',  type: 'string'}
        ]),
        proxy: {
            simpleSortMode: true,
            type: 'direct',
            directFn: appRouter.getTree,
            paramOrder: ['uid']
        }
    });

    Ext.define('Daemons.store.Daemons', {
        extend: 'Ext.data.TreeStore',
        model: 'Daemons.model.Daemon',
        nodeParam: 'uid',
        remoteSort: false,
        sorters: {
            direction: 'asc',
            sorterFn: Zenoss.sortTreeNodes
        }
    });

})();
