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
(function () {
Ext.ns('Zenoss');

Zenoss.FlexButton = Ext.extend(Ext.Button, {
    constructor: function(config) {
        if ( config.menu && config.menu.items && config.menu.items.length == 1 ) {
            // Only has one menu item, lets just not have it display a menu
            config.originalMenu = Ext.apply({}, config.menu);

            // probably don't want to inherit the text
            var menuConfig = config.menu.items[0]
            Ext.apply(config, {listeners: menuConfig.listeners});
            Ext.destroyMembers(config, 'menu');
        }

        Zenoss.FlexButton.superclass.constructor.call(this, config);
    },
    add: function(config) {
        if ( !this.menu ) {
            // this button does not have a menu yet so we need to initialize it
            // update the config with things that may have changed since creation
            var menuConfig = {};
            if ( this.initialConfig.originalMenu ) {
                // originally had a menu, just use it
                Ext.apply(menuConfig, this.initialConfig.originalMenu);
            }
            else {
                // Have to generate a menu config from the original button
                menuConfig.items = [{
                    text: this.getText() ? this.getText() : this.tooltip,
                    listeners: this.initialConfig.listeners
                }];
            }

            // Clear out properties that should be handled by the menu item
            this.on('render', function() {
                this.events['click'].clearListeners();
            }); // *TODO* This code makes me feel dirty; there must be a better way
            this.clearTip();

            this.menu = Ext.menu.MenuMgr.get(menuConfig);
        }

        return this.menu.add(config);
    }
});

Ext.reg('FlexButton', Zenoss.FlexButton);
})();