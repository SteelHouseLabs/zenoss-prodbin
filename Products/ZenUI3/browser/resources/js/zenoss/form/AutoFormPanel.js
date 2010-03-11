/*
 ###########################################################################
 #
 # This program is part of Zenoss Core, an open source monitoring platform.
 # Copyright (C) 2010, Zenoss Inc.
 #
 # This program is free software; you can redistribute it and/or modify it
 # under the terms of the GNU General Public License version 2 as published by
 # the Free Software Foundation.
 #
 # For complete information please visit: http://www.zenoss.com/oss/
 #
 ###########################################################################
 */

/* package level */
(function() {

var ZF = Ext.ns('Zenoss.form');

ZF.AutoFormPanel = Ext.extend(Ext.form.FormPanel, {});

Ext.reg('autoformpanel', ZF.AutoFormPanel);

/*
* Zenoss.form.getGeneratedForm 
* Accepts a uid and a callback.
* Asks the router for a form for the object represented by uid.
* Returns a config object that can be added to a container to render the form.
*/
ZF.getGeneratedForm = function(uid, callback, router) {
    // Router doesn't technically matter, since they all do getInfo, but
    // getForm is definitely defined on DeviceRouter
    router = router || Zenoss.remote.DeviceRouter;
    router.getForm({uid:uid}, function(response){
        callback(Ext.apply({
            xtype:'autoformpanel',
            border: false,
            cls: 'autoformpanel',
            layout: 'column',
            defaults: {
                layout: 'form',
                bodyStyle: 'padding:10px',
                labelAlign: 'top',
                columnWidth: 0.5
            }
        }, response.form));
    });
}

})();
