Ext.onReady(function(){

    /**
     * Base namespace to contain all Zenoss-specific JavaScript.
     */
    Ext.namespace('Zenoss');

    /**
     * Namespace for anonymous scripts to attach data to avoid dumping it into
     * the global namespace.
     */
    Ext.namespace('Zenoss.env');

    /**
     * @class Zenoss.PlaceholderPanel
     * @extends Ext.Panel
     * A custom panel that displays text in its center. This panel is styled
     * with custom CSS to look temporary. It is used to show devs the names of
     * panels and should not be seen by users.
     * @constructor
     * @param {Object} config
     * @cfg {String} text The text to be displayed in the center of the panel.
     */
    Zenoss.PlaceholderPanel = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            Ext.apply(config, {
                cls: 'placeholder',
                layout: 'fit',
                border: false,
                items: [{
                    baseCls: 'inner',
                    border: false,
                    html: config.text,
                    listeners: {'resize':function(ob){
                            ob.getEl().setStyle({'line-height':
                                ob.getEl().getComputedHeight()+'px'});
                    }}
                }]
            });
            Zenoss.PlaceholderPanel.superclass.constructor.apply(
                this, arguments);
        }
    });

    /**
     * @class Zenoss.LargeToolbar
     * @extends Ext.Toolbar
     * A toolbar with greater height and custom CSS class. Used at the top of
     * several screens, including the event console.
     * @constructor
     */
    Zenoss.LargeToolbar = Ext.extend(Ext.Toolbar, { 
        constructor: function(config) {
            Ext.apply(config, {
                cls: 'largetoolbar',
                height: 45,
                border: false
            });
            Zenoss.LargeToolbar.superclass.constructor.apply(
                this, arguments);
        }
    });

    /**
     * @class Zenoss.ExtraHooksSelectionModel
     * @extends Ext.grid.RowSelectionModel
     * A selection model that fires extra events.
     */
    Zenoss.ExtraHooksSelectionModel = Ext.extend(
       Ext.ux.grid.livegrid.RowSelectionModel, {
        initEvents: function() {
            Zenoss.ExtraHooksSelectionModel.superclass.initEvents.call(this);
            this.addEvents('rangeselect');
        },
        selectRange: function (startRow, endRow, keepExisting) {
            this.suspendEvents();
            Zenoss.ExtraHooksSelectionModel.superclass.selectRange.apply(
                this, arguments);
            this.resumeEvents();
            this.fireEvent('rangeselect', this);
        }
    });


    /**
     * @class Zenoss.PostRefreshHookableDataView
     * @extends Ext.DataView
     * A DataView that fires a custom event after the view has refreshed.
     * @constructor
     */
    Zenoss.PostRefreshHookableDataView = Ext.extend(Ext.DataView, {
        constructor: function(config) {
            Zenoss.PostRefreshHookableDataView.superclass.constructor.apply(
                this, arguments);
            this.addEvents(
                /**
                 * @event afterrefresh
                 * Fires after the view has been rendered.
                 * @param {DataView} this
                 */
                'afterrefresh'
            );
        }
    });
    Ext.extend(Zenoss.PostRefreshHookableDataView, Ext.DataView, {
        /**
         * This won't survive upgrade.
         */
        refresh: function(){
            this.clearSelections(false, true);
            this.el.update("");
            var records = this.store.getRange();
            if(records.length < 1){
                if(!this.deferEmptyText || this.hasSkippedEmptyText){
                    this.el.update(this.emptyText);
                }
                this.hasSkippedEmptyText = true;
                this.all.clear();
                return;
            }
            this.tpl.overwrite(this.el, this.collectData(records, 0));
            this.fireEvent('afterrefresh', this)
            this.all.fill(Ext.query(this.itemSelector, this.el.dom));
            this.updateIndexes(0);
        }
    });


    /**
     * @class Zenoss.LiveGridInfoPanel
     * @extends Ext.Toolbar.TextItem
     * Toolbar addition that displays, e.g., "Showing 1-10 of 100 events"
     * @constructor
     * @grid {Object} the GridPanel whose information should be displayed
     */
    Zenoss.LiveGridInfoPanel = Ext.extend(Ext.Toolbar.TextItem, {

        displayMsg : 'Displaying {0} - {1} of {2} events',
        emptyMsg: 'No events',
        cls: 'livegridinfopanel',

        initComponent: function() {
            this.setText(this.emptyMsg);
            if (this.grid) {
                this.grid = Ext.getCmp(this.grid);
                var me = this;
                this.view = this.grid.getView();
                this.view.init = this.view.init.createSequence(function(){
                    me.bind(this);
                }, this.view);
            }
            Zenoss.LiveGridInfoPanel.superclass.initComponent.call(this);
        },
        updateInfo : function(rowIndex, visibleRows, totalCount) {
            var msg = totalCount == 0 ?
                this.emptyMsg :
                String.format(this.displayMsg, rowIndex+1,
                              rowIndex+visibleRows, totalCount);
            this.setText(msg);
        },
        bind: function(view) {
            this.view = view;
            var st = view.ds;

            /*
            st.on('loadexception',   this.enableLoading,  this);
            st.on('beforeload',      this.disableLoading, this);
            st.on('load',            this.enableLoading,  this);
            */
            view.on('rowremoved',    this.onRowRemoved,   this);
            view.on('rowsinserted',  this.onRowsInserted, this);
            view.on('beforebuffer',  this.beforeBuffer,   this);
            view.on('cursormove',    this.onCursorMove,   this);
            view.on('buffer',        this.onBuffer,       this);
            //view.on('bufferfailure', this.enableLoading,  this);

        },
        onCursorMove : function(view, rowIndex, visibleRows, totalCount) {
            this.updateInfo(rowIndex, visibleRows, totalCount);
        },

        onRowsInserted : function(view, start, end) {
            this.updateInfo(view.rowIndex, Math.min(view.ds.totalLength,
                    view.visibleRows-view.rowClipped), view.ds.totalLength);
        },
        onRowRemoved : function(view, index, record) {
            this.updateInfo(view.rowIndex, Math.min(view.ds.totalLength,
                    view.visibleRows-view.rowClipped), view.ds.totalLength);
        },
        beforeBuffer : function(view, store, rowIndex, visibleRows, totalCount,
                                options) {
            //this.loading.disable();
            this.updateInfo(rowIndex, visibleRows, totalCount);
        },
        onBuffer : function(view, store, rowIndex, visibleRows, totalCount) {
            //this.loading.enable();
            this.updateInfo(rowIndex, visibleRows, totalCount);
        }
    });
    Ext.reg('livegridinfo', Zenoss.LiveGridInfoPanel);

    /**
     * @class Zenoss.FilterGridView
     * @extends Ext.grid.GridView
     * A GridView that includes a row below the header with a row filter.
     * @constructor
     */
    Zenoss.FilterGridView = Ext.extend(Ext.ux.grid.livegrid.GridView, {
        rowColors: false,
        constructor: function(config) {
            if (typeof(config.displayFilters)=='undefined')
                config.displayFilters = false;
            Zenoss.FilterGridView.superclass.constructor.apply(this,
                arguments);
        },
        lastOptions: {},
        initEvents: function(){
            Zenoss.FilterGridView.superclass.initEvents.call(this);
            this.addEvents('filterchange');
            this.addEvents('filtertoggle');
            this.addEvents('rowcolorchange');
        },
        initData: function(ds, cm) {
            var store = this.grid.store;

            this.un('beforebuffer', this.onBeforeBuffer,  this);
            cm.un('hiddenchange',   this.updateHeaders,   this);

            this.on('beforebuffer', this.onBeforeBuffer,  this);
            cm.on('hiddenchange',   this.updateHeaders,   this);

            Zenoss.FilterGridView.superclass.initData.call(this, ds, cm);
        },
        // Gather the current values of the filter and apply them to a given
        // object.
        applyFilterParams: function(options) {
            var params = this.lastOptions || {};
            for(i=0;i<this.filters.length;i++){
                var filter = this.filters[i];
                var oldformat;
                query = filter.getValue();
                if (query) {
                    params[filter.id] = query;
                    if (filter.xtype=='datefield'){
                        dt = new Date(query);
                        query = dt.format(
                            Zenoss.date.UniversalSortableDateTime)
                    }
                } else {
                    delete params[filter.id];
                }
            }
            Ext.apply(options.params, {
                params: Ext.util.JSON.encode(params)
            });
            // Store them for later, just in case
            this.lastOptions = params;
        },
        onBeforeLoad: function(store, options) {
            this.applyFilterParams(options);
            return Zenoss.FilterGridView.superclass.onBeforeLoad.call(this,
                store, options);
        },
        onBeforeBuffer: function(view, store, rowIndex, visibleRows,
                                 totalCount, options) {
            this.applyFilterParams(options);
            return true;
        },
        getFilterCt: function() {
            return Ext.select('.x-grid3-filter');
        },
        hideFilters: function() {
            this.setFiltersDisplayed(false);
        },
        showFilters: function() {
            this.setFiltersDisplayed(true);
        },
        setFiltersDisplayed: function(bool) {
            this.displayFilters = bool;
            this.getFilterCt().setDisplayed(bool);
            this.fireEvent('filtertoggle');
            if(bool) this.renderEditors();
            this.layout();
        },
        renderFilterRow: function() {
            var cs = this.getColumnData(), 
                ct = this.templates.cell,
                ct = new Ext.Template( 
                    '<td class="x-grid3-col x-grid3-cell',
                    ' x-grid3-td-{id} {css}" style="{style}" tabIndex="-1"',
                    ' {cellAttr}> <div class="x-grid3-cell-inner',
                    ' x-grid3-col-{id}" unselectable="on" {attr}>',
                    '{value}</div></td>'),
                buf = [],
                p = {},
                rp = {},
                rt = new Ext.Template('<tr {display} class="x-grid3-filter"',
                    '>{cells}</tr>');
            for (i=0,len=cs.length; i<len; i++) {
                if (this.cm.isHidden(i)) continue;
                c = cs[i];
                p.id = c.id;
                p.css = 'x-grid3-cell-filter';
                p.attr ='id="filtergrid-'+c.id+'"';
                p.cellAttr = "";
                p.value = '';
                buf[buf.length] = ct.apply(p);
            }
            rp.tsyle = 'width:'+this.getTotalWidth()+';';
            rp.cols = buf.length;
            rp.cells = buf.join("");
            rp.display = this.displayFilters?'':'style="display:none"'
            return rt.apply(rp);
        },
        filters: [],
        /*
         * this.reset() has an annoying habit of blurring existing filter
         * fields and taking away row stripes. This is the resetting part of
         * the code, but we use updateLiveRows() instead of refresh(), which
         * fixes the problem.
         */
        nonDisruptiveReset: function() {
            this.ds.modified = [];
            //this.grid.selModel.clearSelections(true);
            this.rowIndex      = 0;
            this.lastScrollPos = 0;
            this.lastRowIndex = 0;
            this.lastIndex    = 0;
            this.adjustVisibleRows();
            this.adjustScrollerPos(-this.liveScroller.dom.scrollTop,
                true);
            this.showLoadMask(false);
            //this.reset(false);
            this.updateLiveRows(this.rowIndex, true, true);
        },
        renderEditors: function() {
            Ext.each(this.filters, function(ob){ob.destroy()});
            var cs = this.getColumnData();
            for (i=0,len=cs.length; i<len; i++) {
                if (this.cm.isHidden(i)) continue;
                var c = cs[i],
                    fieldid = c.id,
                    id = 'filtergrid-' + fieldid;
                var config = this.cm.config[i].filter;
                if (!config) config = {xtype:'textfield'};
                Ext.apply(config, {
                    id:fieldid, 
                    enableKeyEvents: true,
                    selectOnFocus: true
                });
                var filter = new Ext.ComponentMgr.create(
                    config?config:{xtype:'textfield', validationDelay:500});
                if (this.lastOptions) {
                    var newValue = this.lastOptions[fieldid];
                    filter.setValue(newValue);
                }
                var panel = new Ext.Panel({
                    frame: false,
                    border: false,
                    layout: 'fit',
                    renderTo: id,
                    items: filter
                });
                filter.setWidth('100%');
                this.filters[this.filters.length] = filter;
                filter.validationTask = new Ext.util.DelayedTask(function(){
                    this.fireEvent('filterchange', this);
                    this.nonDisruptiveReset();
                }, this);
                if (filter.xtype=='textfield') {
                    filter.on('keyup', function(field, e) {
                        if(!e.isNavKeyPress()) this.validationTask.delay(250);
                    }, filter);
                } else {
                    filter.on('select', function(field, e) {
                        this.validationTask.delay(250);
                    }, filter);
                    filter.on('change', function(field, e) {
                        this.validationTask.delay(250);
                    }, filter);
                }
                
            }
        },
        updateHeaders: function() {
            Zenoss.FilterGridView.superclass.updateHeaders.call(this);
            this.renderEditors();
        },
        renderUI: function() {
            Zenoss.FilterGridView.superclass.renderUI.call(this);
            //this.renderEditors();
        },
        renderHeaders : function(){
            html = Zenoss.FilterGridView.superclass.renderHeaders.call(this);
            html = html.slice(0, html.length-8);
            html = html + this.renderFilterRow() + '</table>';
            return html;
        },
        getState: function(){
            return {
                rowColors: this.rowColors,
                displayFilters: this.displayFilters,
                options: this.lastOptions
            };
        },
        getFilterButton: function(){
            return Ext.getCmp(this.filterbutton);
        },
        getRowClass: function(record, index) {
            var stateclass = record.get('eventState')=='New' ? 
                                'unacknowledged':'acknowledged';
            var sev = Zenoss.util.convertSeverity(record.get('severity'));
            var sevclass = this.rowColors ? sev + ' rowcolor' : '';
            return stateclass + ' ' + sevclass;

        },
        toggleRowColors: function(bool){
            this.rowColors = bool;
            this.fireEvent('rowcolorchange');
            this.updateLiveRows(this.rowIndex, true, false);
        },
        applyState: function(state) {
            this.rowColors = state.rowColors;
            this.displayFilters = state.displayFilters;
            this.lastOptions = state.options;
            var btn = Ext.getCmp(this.filterbutton);
            var rowcoloritem = Ext.getCmp(this.rowcoloritem);
            btn.on('render', function(){
                this.toggle(state.displayFilters);
            }, btn);
            rowcoloritem.on('render', function(){
                this.setChecked(state.rowColors);
            }, rowcoloritem);
        },
        resetFilters: function(){
            this.lastOptions = {};
            this.getFilterButton().toggle(false);
        }
    });

    /**
     * @class Zenoss.FilterGridPanel
     * @extends Ext.grid.GridPanel
     * A GridPanel that uses a FilterGridView.
     * @constructor
     */
    Zenoss.FilterGridPanel = Ext.extend(Ext.ux.grid.livegrid.GridPanel, {
        initStateEvents: function(){
            Zenoss.FilterGridPanel.superclass.initStateEvents.call(this);
            this.mon(this.view, 'filterchange', this.saveState, this);
            this.mon(this.view, 'filtertoggle', this.saveState, this);
            this.mon(this.view, 'rowcolorchange', this.saveState, this);
        },
        getView : function(){
            if(!this.view){
                this.view = new Zenoss.FilterGridView(this.viewConfig);
            }
            return this.view;
        },
        restoreURLState: function() {
            var qs = window.location.search.replace(/^\?/, ''),
                state = Ext.urlDecode(qs).state;
            if (state) {
                try {
                    state = Ext.decode(Zenoss.util.base64.decode(state));
                    this.applyState(state);
                } catch(e) { noop(); }
            }
        },
        clearURLState: function() {
            var qs = window.location.search.replace(/^\?/, ''),
                qs = Ext.urlDecode(qs);
            if (qs.state) {
                delete qs.state;
                qs = Ext.urlEncode(qs);
                if (qs) {
                    window.location.search = '?' + Ext.urlEncode(qs);
                } else {
                    window.location.search = ''
                }
            }
        },
        getPermalink: function() {
            var l = window.location,
                path = l.protocol + '//' + l.host + l.pathname;
                st = Zenoss.util.base64.encode(Ext.encode(this.getState()));
            return path + '?state=' + st;
        },
        initState: function() {
            Zenoss.FilterGridPanel.superclass.initState.apply(this, arguments);
            this.restoreURLState();
        },
        getState: function(){
            var val = Zenoss.FilterGridPanel.superclass.getState.call(this);
            var filterstate = this.getView().getState();
            val.filters = filterstate;
            return val
        },
        applyState: function(state){
            this.getView().applyState(state.filters);
            Zenoss.FilterGridPanel.superclass.applyState.apply(this, arguments);
        },
        resetGrid: function() {
            Ext.state.Manager.clear(this.getItemId());
            var view = this.getView();
            view.resetFilters();
            Zenoss.remote.EventConsole.column_config({}, function(result){
                var results = [];
                Ext.each(result, function(r){
                    results[results.length] = Ext.decode(r);
                });
                var cm = new Ext.grid.ColumnModel(results);
                this.store.sortInfo = this.store.defaultSort;
                this.reconfigure(this.store, cm);
                view.fitColumns();
                view.showLoadMask(true);
                view.nonDisruptiveReset();
                this.saveState();
                this.clearURLState();
            }, this);
        },
        hideFilters: function() { this.getView().hideFilters(); },
        showFilters: function() { 
            this.getView().showFilters(); }
    });

    /**
     * @class Zenoss.MultiselectMenu
     * @extends Ext.Toolbar.Button
     * A combobox-like menu that allows one to toggle each option, and is able
     * to deliver its value like a form field.
     * @constructor
     */
    Zenoss.MultiselectMenu = Ext.extend(Ext.Toolbar.Button, {
        constructor: function(config) {
            items = [];
            var me = this;
            Ext.each(config.source, function(o){
                items[items.length] = {
                    checked: typeof(o.checked)=='undefined',
                    hideOnClick: false,
                    handler: function(){
                        me.fireEvent('change');
                    },
                    value: o.value,
                    text: o.text
                }
            });
            config.menu = {
                items: items
            };
            Zenoss.MultiselectMenu.superclass.constructor.apply(this, arguments);
        },
        getValue: function() {
            var result = [];
            Ext.each(this.menu.items.items, function(item){
                if (item.checked) result[result.length] = item.value
            });
            return result;
        },
        setValue: function(val) {
            if (!val) {
                this.constructor(this.initialConfig);
            } else {
                Ext.each(this.menu.items.items, function(item){
                    var shouldCheck = false;
                    try{
                        shouldCheck = val.indexOf(item.value)!=-1;
                    } catch(e) {var _x;}
                    item.setChecked(shouldCheck);
                });
            }
        }

    });
    Ext.reg('multiselectmenu', Zenoss.MultiselectMenu);

    /**
     * @class Zenoss.StatefulRefreshMenu
     * @extends Ext.Menu
     * A refresh menu that is able to save and restore its state.
     * @constructor
     */
    Zenoss.StatefulRefreshMenu = Ext.extend(Ext.menu.Menu, {
        constructor: function(config) {
            config.stateful = true;
            config.stateEvents = ['itemclick'];
            Zenoss.StatefulRefreshMenu.superclass.constructor.apply(this,
                arguments);
        },
        getState: function(){
            return this.trigger.interval;
        },
        applyState: function(interval){
            var items = this.items.items;
            Ext.each(items, function(item){
                if (item.value==interval)
                    item.setChecked(true);
            }, this);
            this.trigger.on('afterrender', function(){
                this.trigger.setInterval(interval);
            }, this);
        }
    });

    Ext.reg('statefulrefreshmenu', Zenoss.StatefulRefreshMenu);

    /**
     * @class Zenoss.RefreshMenu
     * @extends Ext.SplitButton
     * A button that manages refreshing and allows the user to set a polling
     * interval.
     * @constructor
     */
    Zenoss.RefreshMenuButton = Ext.extend(Ext.SplitButton, {
        constructor: function(config) {
            var menu = {
                xtype: 'statefulrefreshmenu',
                id: 'evc_refresh',
                trigger: this,
                items: [{
                    xtype: 'menutextitem',
                    cls: 'refreshevery',
                    text: 'Refresh every'
                },{
                    xtype: 'menucheckitem',
                    text: '1 minute',
                    value: 60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '5 minutes',
                    value: 5*60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '10 minutes',
                    value: 10*60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '30 minutes',
                    value: 30*60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: '1 hour',
                    value: 60*60,
                    group: 'refreshgroup'
                },{
                    xtype: 'menucheckitem',
                    text: 'Manually',
                    value: 0,
                    group: 'refreshgroup'
                }]
            };
            config.menu = menu;
            Zenoss.RefreshMenuButton.superclass.constructor.apply(this,
                arguments);
            this.refreshTask = new Ext.util.DelayedTask(this.poll, this);
            this.menu.on('itemclick', function(item){
                this.setInterval(item.value);
            }, this);
        },
        setInterval: function(interval) {
            this.interval = interval;
            this.refreshTask.delay(this.interval*1000);
        },
        poll: function(){
            if (this.interval) {
                this.handler();
                this.refreshTask.delay(this.interval*1000);
            }
        }
    });
    Ext.reg('refreshmenu', Zenoss.RefreshMenuButton);

   
    // FIXME: Refactor this to be much, much smarter about its own components.
    Zenoss.DetailPanel = Ext.extend(Ext.Panel, {
        isHistory: false,
        constructor: function(config){
            config.onDetailHide = config.onDetailHide || function(){var _x;};
            config.layout = 'border';
            config.border = false;
            config.defaults = {border:false};
            config.items = [{
                id: 'evdetail_hd',
                region: 'north',
                layout: 'border',
                height: 50,
                cls: 'evdetail_hd',
                defaults: {border: false},
                items: [{
                    region: 'west',
                    width: 77,
                    layout: 'hbox',
                    defaults: {border: false},
                    items: [{
                        id: 'severity-icon',
                        cls: 'severity-icon'
                    },{
                        id: 'evdetail-sep',
                        cls: 'evdetail-sep'
                    }]
                },{
                    region: 'center',
                    id: 'evdetail-summary',
                    html: ''
                },{
                    region: 'east',
                    id: 'evdetail-tools',
                    layout: 'hbox',
                    width: 57,
                    defaults: {border: false},
                    items: [{
                        id: 'evdetail-popout',
                        cls: 'evdetail-popout'
                    },{
                        id: 'evdetail_tool_close',
                        cls: 'evdetail_close'
                    }]
                }]
            },{
                id: 'evdetail_bd',
                region: 'center',
                defaults: {
                    frame: false,
                    border: false
                },
                autoScroll: true,
                layout: 'table',
                layoutConfig: {
                    columns: 1,
                    tableAttrs: {
                        style: {
                            width: '90%'
                        }
                    }
                },
                cls: 'evdetail_bd',
                items: [{
                    id: 'evdetail_props',
                    cls: 'evdetail_props',
                    html: ''
                },{
                    id: 'show_details',
                    cls: 'show_details',
                    hidden: true,
                    html: 'Show more details...'
                },{
                    id: 'full_event_props',
                    cls: 'full_event_props',
                    hidden: true,
                    html: ''
                },{
                    id: 'evdetail-log-header',
                    cls: 'evdetail-log-header',
                    hidden: true,
                    html: '<'+'hr/><'+'h2>LOG<'+'/h2>'
                },{
                    xtype: 'form',
                    id: 'log-container',
                    defaults: {border: false},
                    frame: true,
                    layout: 'table',
                    style: {'margin-left':'3em'},
                    hidden: true,
                    labelWidth: 1,
                    items: [{
                        id: 'detail-logform-evid',
                        xtype: 'hidden',
                        name: 'evid'
                    },{
                        style: 'margin:0.75em',
                        width: 300,
                        xtype: 'textfield',
                        name: 'message',
                        id: 'detail-logform-message'
                    },{
                        xtype: 'button',
                        type: 'submit',
                        name: 'add',
                        text: 'Add',
                        handler: function(btn, e){
                            var form = Ext.getCmp('log-container'),
                                vals = form.getForm().getValues();
                            params = {history:this.isHistory};
                            Ext.apply(params, vals);
                            Zenoss.remote.EventConsole.write_log(
                             params,
                             function(provider, response){
                                 Ext.getCmp(
                                     'detail-logform-message').setRawValue('');
                                 Ext.getCmp(config.id).load(
                                     Ext.getCmp(
                                         'detail-logform-evid').getValue()
                                 );
                            });
                        }
                    }],
                },{
                    id: 'evdetail_log',
                    cls: 'log-content',
                    hidden: true
                }]
            }]
            Zenoss.DetailPanel.superclass.constructor.apply(this, arguments);
        },
        setSummary: function(summary){
            var panel = Ext.getCmp('evdetail-summary');
            panel.el.update(summary);
        },
        setSeverityIcon: function(severity){
            var panel = Ext.getCmp('severity-icon');
            this.clearSeverityIcon();
            panel.addClass(severity);
        },
        clearSeverityIcon: function() {
            var panel = Ext.getCmp('severity-icon');
            Ext.each(Zenoss.env.SEVERITIES,
                function(sev){
                    var sev = sev[1];
                    panel.removeClass(sev.toLowerCase());
                }
            );
        },
        update: function(event) {
            var top_prop_template = new
                Ext.XTemplate.from('detail_table_template');
            var full_prop_template = new
                Ext.XTemplate.from('fullprop_table_template');
            var log_template = new Ext.XTemplate.from('log_table_template');
            var severity = Zenoss.util.convertSeverity(event.severity),
                html = top_prop_template.applyTemplate(event),
                prophtml = full_prop_template.applyTemplate(event),
                loghtml = log_template.applyTemplate(event);

            this.setSummary(event.summary);
            this.setSeverityIcon(severity);
            Ext.getCmp('evdetail_props').el.update(html);
            Ext.getCmp('full_event_props').el.update(prophtml);
            Ext.getCmp('evdetail_log').el.update(loghtml);
            Ext.getCmp('detail-logform-evid').setValue(event.evid);
        },
        wipe: function(){
            this.clearSeverityIcon();
            this.setSummary('');
            Ext.getCmp('show_details').hide();
            Ext.getCmp('evdetail-log-header').hide();
            Ext.getCmp('evdetail_log').hide();
            Ext.getCmp('evdetail_props').hide();
            Ext.getCmp('full_event_props').hide();
            Ext.getCmp('log-container').hide();
        },
        show: function(){
            Ext.getCmp('show_details').show();
            Ext.getCmp('evdetail-log-header').show();
            Ext.getCmp('evdetail_log').show();
            Ext.getCmp('evdetail_props').show();
            if (this.isPropsVisible)
                Ext.getCmp('full_event_props').show();
            Ext.getCmp('log-container').show();
        },
        isPropsVisible: false,
        showProps: function(){
            el = Ext.getCmp('full_event_props');
            tgl = Ext.getCmp('show_details');
            if (!el.hidden){
                el.hide();
                this.isPropsVisible = false;
                tgl.body.update('Show more details...');
            } else {
                el.show();
                this.isPropsVisible = true;
                tgl.body.update('Hide details');
            }
        },
        popout: function(){
             var evid = Ext.getCmp('detail-logform-evid').getValue(),
                 url = this.isHistory ? 'viewHistoryDetail' : 'viewDetail'
             window.open(url + '?evid='+ evid, evid,
                 "status=1,width=600,height=500");
        },
        bind: function(){
            var showlink = Ext.getCmp('show_details').getEl(),
                btn = Ext.getCmp('evdetail_tool_close').getEl(),
                pop = Ext.getCmp('evdetail-popout').getEl();

            showlink.un('click', this.showProps);
            showlink.on('click', this.showProps);

            btn.un('click', this.onDetailHide);
            btn.on('click', this.onDetailHide);

            pop.un('click', this.popout, this);
            pop.on('click', this.popout, this);
        },
        load: function(event_id){
            Zenoss.remote.EventConsole.detail({
                    evid:event_id, 
                    history:this.isHistory
                }, 
                function(result){
                    var event = result.event[0];
                    this.update(event);
                    this.bind();
                    this.show();
                }, this
            );
        }
    });
    Ext.reg('detailpanel', Zenoss.DetailPanel);

    /**
     * General utilities
     */
    Ext.namespace('Zenoss.util');

    Zenoss.env.SEVERITIES = [
        [5, 'Critical'],
        [4, 'Error'],
        [3, 'Warning'],
        [2, 'Info'],
        [1, 'Debug'],
        [0, 'Clear']
    ];

    Zenoss.util.convertSeverity = function(severity){
        sevs = ['clear', 'debug', 'info', 'warning', 'error', 'critical'];
        return sevs[severity];
    }

    Zenoss.util.convertStatus = function(stat){
        var stati = ['New', 'Acknowledged', 'Suppressed'];
        return stati[stat];
    }

    Zenoss.util.render_severity = function(sev) {
        return '<div class="severity-icon-small '+
            Zenoss.util.convertSeverity(sev) +
            '"'+'><'+'/div>'
    }

    Zenoss.util.render_status = function(stat) {
        return '<div class="status-icon-small '+stat.toLowerCase()+'"><'+'/div>';
    }

    Zenoss.util.render_linkable = function(name, col, record) {
        var url = record.data[col.id + '_url'];
        if (url) {
            return '<a href="'+url+'">'+name+'</a>'
        } else {
            return name;
        }
    }

    Zenoss.util.base64 = {
        base64s : "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_",
        encode: function(decStr){
            if (typeof btoa === 'function') {
                 return btoa(decStr);            
            }
            var base64s = this.base64s;
            var bits;
            var dual;
            var i = 0;
            var encOut = "";
            while(decStr.length >= i + 3){
                bits = (decStr.charCodeAt(i++) & 0xff) <<16 | 
                       (decStr.charCodeAt(i++) & 0xff) <<8 | 
                       decStr.charCodeAt(i++) & 0xff;
                encOut += base64s.charAt((bits & 0x00fc0000) >>18) + 
                          base64s.charAt((bits & 0x0003f000) >>12) + 
                          base64s.charAt((bits & 0x00000fc0) >> 6) + 
                          base64s.charAt((bits & 0x0000003f));
            }
            if(decStr.length -i > 0 && decStr.length -i < 3){
                dual = Boolean(decStr.length -i -1);
                bits = ((decStr.charCodeAt(i++) & 0xff) <<16) | (dual ? (decStr.charCodeAt(i) & 0xff) <<8 : 0);
                encOut += base64s.charAt((bits & 0x00fc0000) >>18) + 
                          base64s.charAt((bits & 0x0003f000) >>12) + 
                          (dual ? base64s.charAt((bits & 0x00000fc0) >>6) : '=') + '=';
            }
            return(encOut);
        },
        decode: function(encStr){
            if (typeof atob === 'function') {
                return atob(encStr); 
            }
            var base64s = this.base64s;        
            var bits;
            var decOut = "";
            var i = 0;
            for(; i<encStr.length; i += 4){
                bits = (base64s.indexOf(encStr.charAt(i)) & 0xff) <<18 | 
                       (base64s.indexOf(encStr.charAt(i +1)) & 0xff) <<12 | 
                       (base64s.indexOf(encStr.charAt(i +2)) & 0xff) << 6 | 
                       base64s.indexOf(encStr.charAt(i +3)) & 0xff;
                decOut += String.fromCharCode((bits & 0xff0000) >>16, 
                                              (bits & 0xff00) >>8, bits & 0xff);
            }
            if(encStr.charCodeAt(i -2) == 61){
                return(decOut.substring(0, decOut.length -2));
            }
            else if(encStr.charCodeAt(i -1) == 61){
                return(decOut.substring(0, decOut.length -1));
            }
            else {
                return(decOut);
            }
        }
    }; 
    

    /**
     * Zenoss date patterns and manipulations
     */
    Ext.namespace('Zenoss.date');

    /**
     * A set of useful date formats. All dates should come from the server as
     * ISO8601Long, but we may of course want to render dates in many different
     * ways.
     */
    Ext.apply(Zenoss.date, {
        ISO8601Long:"Y-m-d H:i:s",
        ISO8601Short:"Y-m-d",
        ShortDate: "n/j/Y",
        LongDate: "l, F d, Y",
        FullDateTime: "l, F d, Y g:i:s A",
        MonthDay: "F d",
        ShortTime: "g:i A",
        LongTime: "g:i:s A",
        SortableDateTime: "Y-m-d\\TH:i:s",
        UniversalSortableDateTime: "Y-m-d H:i:sO",
        YearMonth: "F, Y"
    });

});
