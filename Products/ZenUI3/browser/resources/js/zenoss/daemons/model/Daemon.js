/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    var router = Zenoss.remote.ApplicationRouter;

    Ext.define('Daemons.model.Daemon', {
        extend: 'Ext.data.Model',
        fields: Zenoss.model.BASE_TREE_FIELDS.concat([
            {name: 'id',  type: 'string'},
            {name: 'name',  type: 'string'},
            {name: 'uid',  type: 'string'},
            {name: 'uuid',  type: 'string'},
            {name: 'status',  type: 'string'},
            {name: 'enabled',  type: 'boolean'},
            {name: 'isRestarting',  type: 'boolean'},
            {name: 'qtip',  type: 'string'}
        ]),

        proxy: {
            simpleSortMode: true,
            type: 'direct',
            directFn: router.getTree,
            paramOrder: ['uid']
        }
    });

    Ext.define('Daemons.store.Daemons', {
        extend: 'Ext.data.TreeStore',
        model: 'Daemons.model.Daemon',
        nodeParam: 'uid'
    });

})();
