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

(function(){

Zenoss.SlidingCardLayout = Ext.extend(Ext.layout.CardLayout, {
    setActiveItem: function(index) {
        var C = this.container,
            B = C.body,
            card = C.getComponent(index),
            active = this.activeItem,
            activeIndex = C.items.items.indexOf(active);
        if(card!=active) {
            if(active) {
                if(card) {
                    C.fireEvent('beforecardchange', C, card, index, active, activeIndex);
                    if (!card.rendered) {
                        this.renderItem(card, index, C.getLayoutTarget());
                    }
                    card.show();
                    if(card.doLayout && (this.layoutOnCardChange ||
                                         !card.rendered)) {
                        card.doLayout();
                    }
                    var _done = 0;
                    function shiftsCallback() {
                        _done++;
                        if (_done==2)
                            C.fireEvent('cardchange', C, card, index, active,
                                        activeIndex);
                    }
                    var x = B.getX(),
                        w = B.getWidth(),
                        s = [x - w, x + w],
                        cfg = {
                            duration: 0.25,
                            easing: 'easeInStrong',
                            opacity: 0,
                            callback: shiftsCallback
                        };
                    card.el.setY(B.getY());
                    card.el.setX((activeIndex < index ? s[1] : s[0]));
                    active.el.shift(Ext.applyIf({
                        x: activeIndex < index ? s[0] : s[1]
                    }, cfg));
                    card.el.shift(Ext.applyIf({
                        x:x,
                        opacity: 1
                    }, cfg));
                }
            }
            this.activeItem = card;
            this.layout();
        }

    }

});

Ext.Container.LAYOUTS['slide'] = Zenoss.SlidingCardLayout;


Zenoss.HorizontalSlidePanel = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        this.headerText = new Ext.Toolbar.TextItem({
            html: (config && config.text) ? config.text : ''
        });
        config = Ext.applyIf(config || {}, {
            cls: 'subselect',
            border: false,
            defaults: {
                border: false
            },
            layout: 'slide',
            activeItem: 0
        });
        var items = [];
        Ext.each(config.items, function(item, index){
            var headerText = new Ext.Toolbar.TextItem({
                html: (item && item.text) ? item.text : ''
            });
            var navButton = new Ext.Button({
                text: (item && item.buttonText) ? item.buttonText : '',
                cls: index ? 'toleft' : 'toright',
                handler: function() {
                    this.layout.setActiveItem(index ? 0 : 1);

                },
                scope: this
            }, this);
            navButton.hide();
            items.push({
                layout: 'fit',
                border: false,
                defaults: {
                    border: false
                },
                tbar: {
                    border: false,
                    cls: 'subselect-head',
                    height: 37,
                    items: [headerText, '->', navButton]
                },
                items:[item],
                listeners: {
                    render: function(card) {
                        card.card = card.items.items[0];
                        card.card.parentCard = card;
                        card.headerText = headerText;
                        card.navButton = navButton;
                        var setHeaderText = function(text, qtip) {
                            this.headerText.setText(text);
                            Ext.QuickTips.unregister(this.headerText);

                            if ( qtip ) {
                                Ext.QuickTips.register({
                                    target: this.headerText,
                                    text: qtip
                                });
                            }
                        };
                        var setButtonText = function(text) {
                            this.navButton.setText(text);
                        };
                        card.setHeaderText = setHeaderText.createDelegate(card);
                        card.setButtonText = setButtonText.createDelegate(card);
                    }
                }
            });
        }, this);
        config.items = items;
        Zenoss.HorizontalSlidePanel.superclass.constructor.call(this, config);
    },
    initEvents: function() {
        this.addEvents('beforecardchange');
        this.addEvents('cardchange');
        Zenoss.HorizontalSlidePanel.superclass.initEvents.call(this);
    }
});

Ext.reg('horizontalslide', Zenoss.HorizontalSlidePanel);

/**
 * A MixedCollection for nav configs.
 *
 * Each item in the config is a normal dictionary with an xtype. The xtype specified will be used for the display
 * when the item is clicked.
 *
 * Example item structure:
 *
 * {
 *     text: 'Menu label',
 *     id: 'View id',
 *     xtype: 'somextype', // optional, defaults to Panel
 *     filterNav: function(navTree) {
 *         // An optional function that is called to determine if this item should be shown
 *         // Use navTree.contextUid for the context.
 *         // return true to display the item or false to remove it
 *     }
 * }
 */
Zenoss.NavConfig = Ext.extend(Ext.util.MixedCollection, {
    constructor: function() {
        Zenoss.NavConfig.superclass.constructor.call(this, true, function(item) {
            return item.id;
        });
    }
});

Zenoss.NavManager = Ext.extend(Object, {
    all: null,
    constructor: function() {
        this.all = new Zenoss.NavConfig();
        this.all.addEvents('navready');
    },
    /**
     * Register a nav item tree. See `Zenoss.NavConfig` for item structure.
     *
     * Zenoss.nav.register({
     *     DeviceGroup: [
     *         {
     *             id: 'device_grid',
     *             text: 'Devices',
     *             listeners: {
     *                 render: updateNavTextWithCount
     *             }
     *         },
     *         {
     *             id: 'events_grid',
     *             text: _t('Events')
     *         }
     *     ]
     * });
     *
     * @param navSpec
     */
    register: function(navSpec) {
        for ( var type in navSpec ) {
            this.add(type, navSpec[type]);
        }
    },
    /**
     * Adds a nav of `type` with its `items`. If a nav of `type` already exists, the items are appended.
     *
     * @param type Type of nav menu to add (ex: Device, DeviceGroup)
     * @param items An array of nav items. See `Zenoss.NavConfig` for item structure.
     */
    add: function(type, items) {
        if ( !this.all.containsKey(type) ) {
            // Create an empty nav container
            var newNav = new Zenoss.NavConfig();
            newNav.id = type;
            this.all.add(type, newNav);

            this.appendTo(type, items);

            this.all.fireEvent('navready', newNav);
        }
        else {
            this.appendTo(type, items);
        }
    },
    /**
     * Get a nav config if it exists.
     *
     * @param type
     */
    get: function(type) {
        return this.all.key(type);
    },
    /**
     * Add menu nodes to the end of a nav config
     *
     * @param type Nav config type
     * @param items Array of items. See `Zenoss.NavConfig` for item structure.
     */
    appendTo: function(type, items) {
        if ( this.all.containsKey(type) ) {
            var nav = this.all.key(type);
            nav.addAll(items);
        }
        else {
            this.onAvailable(type, function(item) {
                item.addAll(items);
            });
        }
    },
    /**
     * Registers a callback to be called as soon as a nav tree matching navId is added.
     *
     * @param navId
     * @param callback
     */
    onAvailable: function(navId, callback, scope) {
        function onAdd(item) {
            if ( item.id == navId ) {
                callback.call(scope || item, item);
                this.all.un('navready', onAdd, scope);
            }
        }

        this.all.on('navready', onAdd, this);
    }
});

Zenoss.nav = new Zenoss.NavManager();

Zenoss.SubselectionNodeUI = Ext.extend(Ext.tree.TreeNodeUI, {
    render: function() {
        Zenoss.SubselectionNodeUI.superclass.render.call(this);
        Ext.removeNode(this.getIconEl());
    }
});

Zenoss.SubselectionNode = Ext.extend(Ext.tree.TreeNode, {
    constructor: function(config) {
        Ext.applyIf(config, {
            leaf: true,
            uiProvider: Zenoss.SubselectionNodeUI
        });
        Zenoss.SubselectionNode.superclass.constructor.call(this, config);
        this.addEvents('render');
    },
    render: function(bulkRender) {
        Zenoss.SubselectionNode.superclass.render.call(this, bulkRender);
        this.fireEvent('render', this);
    }

});

Ext.tree.TreePanel.nodeTypes.subselect = Zenoss.SubselectionNode;


Zenoss.SubselectionPanel = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        var id = config.id || Ext.id();
        Ext.applyIf(config, {
            id: id,
            layout: 'fit',
            border: false,
            bodyStyle: { 'margin-top' : 10 },
            items: [{
                xtype:'treepanel',
                ref: 'treepanel',
                selModel: new Ext.tree.DefaultSelectionModel({
                    listeners: {
                        selectionchange: function(sm, node) {
                            if (node) {
                                var action = node.attributes.action;
                                if (action) {
                                    if (Ext.isString(this.target)) {
                                        this.target = Ext.getCmp(this.target);
                                    }
                                    action.call(node, node, this.target);
                                }
                            }
                        },
                        scope: this
                    }
                }),
                id: 'subselecttreepanel' + id,
                border: false,
                rootVisible: false,
                root : {nodeType: 'node'}            }]
        });
        Zenoss.SubselectionPanel.superclass.constructor.call(this, config);
    },
    initComponent: function() {
        Zenoss.SubselectionPanel.superclass.initComponent.call(this);
        this.treepanel = Ext.getCmp('subselecttreepanel' + this.id);
    },
    setContext: function(uid) {
        var type = Zenoss.types.type(uid),
            nodes = Zenoss.nav.get(type);
        if (nodes) {
            Zenoss.util.each(nodes, function(node) {
                Ext.applyIf(node, {
                    nodeType: 'subselect'
                });
            });
            var root = new Ext.tree.AsyncTreeNode({
                children: nodes,
                listeners: {
                    load: function(node){
                        var toselect = node.firstChild;
                        if (toselect) {
                            if (toselect.rendered) {
                                toselect.select();
                            } else {
                                toselect.on('render', function(node){
                                    node.select();
                                });
                            }
                        }
                    },
                    scope: this
                }
            });
            this.treepanel.setRootNode(root);
        }
    }
});

Zenoss.DetailNavTreePanel = Ext.extend(Ext.tree.TreePanel, {
    constructor: function(config){
        Ext.applyIf(config, {
            useArrows: true,
            autoHeight: true,
            selModel: new Zenoss.BubblingSelectionModel({
                bubbleTarget: config.bubbleTarget
            }),
            id: 'subselecttreepanel' + config.idSuffix,
            ref: 'subselecttreepanel',
            border: false,
            rootVisible: false,
            cls: 'x-tree-noicon',
            root : {nodeType: 'node'}
        });
        Zenoss.DetailNavTreePanel.superclass.constructor.call(this, config);
    }
});
Ext.reg('detailnavtreepanel', Zenoss.DetailNavTreePanel);

Ext.reg('subselection', Zenoss.SubselectionPanel);
/**
 * Used to manage and display detail navigation tree for a contextId
 *
 * @class Zenoss.DetailNavPanel
 * @extends Zenoss.SubselectionPanel
 */
Zenoss.DetailNavPanel = Ext.extend(Zenoss.SubselectionPanel,{
    /**
     * @cfg {function} onGetNavConfig abstract function; hook to provide more nav items
     * @param {string} uid; item to get nav items for
     */
    onGetNavConfig: function(uid){ return []; },
    /**
     * Called when an item in detail nav is selected
     * @param {object} this, the DetailNavPanel
     * @param {object} the navigation node selected
     */
    onSelectionChange: Ext.emptyFn,
    /**
     * Filter out from being in the detail nav; used to filter out nav nodes
     * and the content panels. Return true if it should be kept, false otherwise
     * @param {DetailNavPanel}
     * @param {Object} config
     */
    filterNav: function(detailNav, config) {return true;},
    /**
     * The object id for which the detail navigation belongs to
     */
    contextId: null,
    /**
     * Menu ids used to get non dialog menus to be used in navigation;
     * Empty or null if no nav from old menu items is desired
     */
    menuIds: ['More','Manage','Edit', 'Actions','Add','TopLevel'],
    /**
     * map of nav id to panel configuration
     */
    loaded: false,
    panelConfigMap: null,
    selectFirstNode: true,
    constructor: function(config) {
        Ext.applyIf(config, {
            id: Ext.id(),
            bodyCssClass: 'detailnav',
            layout: 'fit',
            border: false,
            bodyStyle: { 'margin-top' : 10 }
        });
        // call second applyIf so config.id is set correctly
        Ext.applyIf(config, {
            items: {
                xtype: 'detailnavtreepanel',
                ref: 'navtreepanel',
                idSuffix: config.id,
                bubbleTarget: config.bubbleTarget
            }
        });
        Zenoss.DetailNavPanel.superclass.constructor.call(this, config);
    },
    initEvents: function() {
        this.addEvents(
            /**
             * @event navloaded
             * Fires after the navigation has been loaded
             * @param {DetailNavPanel} this The DetailNavPanel
             * @param {AsyncTreeNode} root The root node
             */
             'navloaded',
             /*
             * @event nodeloaded
             * Fires after each navigation node has been loaded
             * @param {DetailNavPanel} this The DetailNavPanel
             * @param {Object} The Navigation config loaded
             */
             'nodeloaded',
            /**
             * @event contextchange
             * Fires after the navigation has been loaded
             * @param {DetailNavPanel} this The DetailNavPanel
             */
            'contextchange'
        );
        Zenoss.DetailNavPanel.superclass.initEvents.call(this);
        if (this.selectFirstNode) {
            this.on('navloaded', this.selectFirst, this);
        }
    },
    setContext: function(uid) {
        //called to load the nav tree
        this.loaded = false;
        this.contextId = uid;
        this.treepanel.setRootNode([]);
        this.getNavConfig(uid);
        this.fireEvent('contextchange', this);
    },
    getSelectionModel: function() {
        return this.treepanel.getSelectionModel();
    },
    getNavConfig: function(uid){
        //Direct call to get nav configs from server
        var me = this;
        var myCallback = function(provider, response) {
            var detailConfigs = response.result.detailConfigs;
            var filterFn = function(val) {
                var show = true;
                if (  Ext.isFunction(val.filterNav) ) {
                    show = val.filterNav(me);
                }

                return show && me.filterNav(me, val);
            };

            detailConfigs = Zenoss.util.filter(detailConfigs, filterFn, me);

            var nodes = me.onGetNavConfig(me.contextId);
            if (!Ext.isDefined(nodes) || nodes === null) {
                nodes = [];
            }

            nodes = Zenoss.util.filter(nodes, filterFn, me);

            if ( detailConfigs ) {
                nodes = nodes.concat(detailConfigs);
            }

            me.panelConfigMap = [];
            Zenoss.util.each(nodes, function(val) {
                me.panelConfigMap[val.id] = val;
            });

            me.setNavTree(nodes);
        };
        var args = {
            'uid': uid
        };
        if (this.menuIds !== null && this.menuIds.length >= 1){
            args['menuIds'] = this.menuIds;
        }
        Zenoss.remote.DetailNavRouter.getDetailNavConfigs(args, myCallback, this);
    },
    reset: function() {
        var root = new Ext.tree.AsyncTreeNode();
        this.treepanel.setRootNode(root);
        return root;
    },
    selectFirst: function(me, root) {
        var sel = root.getOwnerTree().getSelectionModel().getSelectedNode(),
            token = Ext.History.getToken(),
            firstToken = me.id + Ext.History.DELIMITER + root.firstChild.id;
        if (!sel) {
            if (!token || (token && token==firstToken)) {
                root.firstChild.select();
            }
        }
    },
    /**
     * Set the nodes to display in the nav tree.
     * @param nodes Zenoss.NavConfig Nodes to set the nav to
     */
    setNavTree: function(nodes){
        //get any configs registered by the page
        var root;
        if (nodes) {
            root = this.reset();
            Zenoss.util.each(nodes, function(node){
                Ext.applyIf(node, {
                    nodeType: 'subselect'
                });
                root.appendChild(node);
            });

            // Send an alert for all nodes after all nodes have been loaded
            Zenoss.util.each(nodes, function(navConfig){
                this.fireEvent('nodeloaded', this, navConfig);
            }, this);
        }
        this.loaded = true;
        this.fireEvent('navloaded', this, root);
    }
});
Ext.reg('detailnav', Zenoss.DetailNavPanel);


Zenoss.DetailNavCombo = Ext.extend(Ext.form.ComboBox, {
    target: null,
    contextUid: null,
    lastSelItem: null,
    panelConfigMap: null,
    mode: 'local',
    editable: false,
    forceSelection: true,
    typeAhead: false,
    triggerAction: 'all',
    filterNav: function(config) {return true;},
    menuIds: ['More','Manage','Edit', 'Actions','Add','TopLevel'],
    onSelectionChange: Ext.emptyFn,
    onGetNavConfig: function(uid){ return []; },
    getTarget: function() {
        var target = this.target;
        return Ext.isString(target) ? Ext.getCmp(target) : target;
    },
    initEvents: function() {
        Zenoss.DetailNavCombo.superclass.initEvents.call(this);
        this.on('select', this.onItemSelected, this);
    },
    onItemSelected: function(me, item){
        var target = this.getTarget(),
            id = item.id,
            config = this.panelConfigMap[id],
            action = config.action || function(node, target) {
                if (!(id in target.items.map)) {
                    Ext.applyIf(config, {refreshOnContextChange: true});
                    if(config) {
                        target.add(config);
                        target.doLayout();
                    }
                }
                target.items.map[id].setContext(this.contextUid);
                target.layout.setActiveItem(id);
            };
        this.lastSelItem = item;
        action.call(this, item, target, this);
    },
    selectAt: function(idx) {
        var record = this.store.getAt(idx);
        this.lastSelItem = record;
        this.onSelect(record, idx);
    },
    selectByItem: function(item) {
        var idx = 0;
        if (item) {
            idx = this.store.indexOfId(item.id);
            if (idx < 0) {
                idx = 0;
            }
        }
        this.selectAt(idx);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        var args = {uid:uid};
        if (!Ext.isEmpty(this.menuIds)) {
            args.menuIds = this.menuIds;
        }
        Zenoss.remote.DetailNavRouter.getDetailNavConfigs(args, function(r){
            var detailConfigs = r.detailConfigs,
                items = [],
                nodes = [],
                panelMap = {};

            var filterFn = function(val) {
                var show = true;
                if (  Ext.isFunction(val.filterNav) ) {
                    show = val.filterNav(this);
                }

                return show && this.filterNav(val);
            };

            nodes = this.onGetNavConfig(uid);
            nodes = Zenoss.util.filter(nodes, filterFn, this);

            detailConfigs = Zenoss.util.filter(detailConfigs, filterFn, this);
            nodes = nodes.concat(detailConfigs);

            Ext.each(nodes, function(cfg){
                items.push([cfg.id, cfg.text]);
                panelMap[cfg.id] = cfg;
            });

            this.panelConfigMap = panelMap;
            this.store = new Ext.data.ArrayStore({
                'id':0,
                fields: ['value', 'text'],
                data: items,
                autoDestroy: true
            });
            this.valueField = 'value';
            this.displayField = 'text';
            this.list = null;
            this.initList();
            // "sticky" menu selection, show same item as was shown for last context
            this.selectByItem(this.lastSelItem);
        }, this);
    }
});

Ext.reg('detailnavcombo', Zenoss.DetailNavCombo);

Zenoss.DetailContainer = Ext.extend(Ext.Panel, {
    constructor: function(config){
        Ext.applyIf(config, {
            border: false,
            autoScroll: true,
            listeners: {
                selectionchange: this.onSelectionChange,
                scope: this
            }
        });
        Ext.each(config.items, function(item){
            item.bubbleTarget = this;
        }, this);
        Zenoss.DetailContainer.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.items.each(function(item){
            item.setContext(uid);
        });
    },
    onSelectionChange: function(eventSelModel, node) {
        var itemSelModel;
        this.items.each(function(item){
            itemSelModel = item.getSelectionModel();
            if ( itemSelModel === eventSelModel ) {
                item.onSelectionChange(node);
            } else {
                if ( itemSelModel.getSelectedNode() ) {
                    itemSelModel.getSelectedNode().unselect(true);
                }
            }
        });
    }
});
Ext.reg('detailcontainer', Zenoss.DetailContainer);

})();
