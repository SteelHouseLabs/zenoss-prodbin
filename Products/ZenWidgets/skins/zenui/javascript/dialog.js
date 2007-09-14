var Class={
    create:function(){
        return function(){
            this.__init__.apply(this,arguments);
        }
    }
}

function getFormElements(parentbox) {
    var firstElement;
    var textBoxes = [];
    var submitButtons = [];
    var formElements = [];
    var traverse = function(node) {
        if ((node.tagName=='SELECT'||node.tagName=='INPUT'||
            node.tagName=='TEXTAREA')&&node.type!='hidden') {
                formElements[formElements.length]=node;
                if (!firstElement) 
                    firstElement = node;
        }
        if (node.tagName=='INPUT'&&(node.type=='text'||node.type=='password'))
            textBoxes[textBoxes.length]=node;
        if (node.tagName=='INPUT'&&(node.type=='submit'||node.type=='button')&&
            node.id!='dialog_cancel')
            submitButtons[submitButtons.length] = node;
        if (node.childNodes != null) {
            for (var i=0;i<node.childNodes.length;i++) {
                traverse(node.childNodes.item(i));
            }
        }
    }
    traverse(parentbox);
    return [firstElement, textBoxes, submitButtons, formElements]
}

var Dialog = {};
Dialog.Box = Class.create();
Dialog.Box.prototype = {
    __init__: function(id) {
        bindMethods(this);
        this.makeDimBg();
        this.box = $(id);
        this.framework = DIV(
            {'class':'dialog_container'},
            [
            //top row
            DIV({'class':'dbox_tl'},
             [ DIV({'class':'dbox_tr'},
               [ DIV({'class':'dbox_tc'}, null)])]),
            //middle row
            DIV({'class':'dbox_ml'},
             [ DIV({'class':'dbox_mr'},
               [ DIV({'class':'dbox_mc',
                      'id':'dialog_content'}, null)])]),
            //bottom row
            DIV({'class':'dbox_bl'},
             [ DIV({'class':'dbox_br'},
               [ DIV({'class':'dbox_bc'}, null)])])
            ]);
        insertSiblingNodesBefore(this.box, this.framework);
        setStyle(this.framework, {'position':'absolute'});
        removeElement(this.box);
        appendChildNodes($('dialog_content'), this.box);
        this.loadEvents = {};
        this.box.addLoadEvent = bind(this.addLoadEvent, this);
        this.box.show = bind(this.show, this);
        this.box.hide = bind(this.hide, this);
        this.box.fill = bind(this.fill, this);
        this.box.submit_form = bind(this.submit_form, this);
        this.box.submit_form_and_check = bind(this.submit_form_and_check, this);
        this.parentElem = this.box.parentNode;
        this.defaultContent = this.box.innerHTML
        setStyle(this.box, {
            'position':'absolute',
            'z-index':'5001',
            'display':'none'});
    },
    addLoadEvent: function(id, func) {
        if (!(id in this.loadEvents)) this.loadEvents[id] = [];
        this.loadEvents[id].push(func);
    },
    makeDimBg: function() {
        if($('dialog_dim_bg')) {
            this.dimbg = $('dialog_dim_bg');
        } else {
            this.dimbg = DIV({'id':'dialog_dim_bg'},null);
            setStyle(this.dimbg, {
                'position':'absolute',
                'top':'0',
                'left':'0',
                'z-index':'5000',
                'width':'100%',
                'background-color':'white',
                'display':'none'
            });
            insertSiblingNodesBefore(document.body.firstChild, this.dimbg);
        }
    },
    moveBox: function(dir) {
        this.framework = removeElement(this.framework);
        if(dir=='back') {
            this.framework = this.dimbg.parentNode.appendChild(this.framework);
        } else {
            this.framework = this.dimbg.parentNode.insertBefore(
                this.framework, this.dimbg);
        }
    },
    lock: new DeferredLock(),
    show: function(form, url) {
        var d1 = this.lock.acquire();
        d1.addCallback(bind(function() {
            if (url) this.fetch(url);
        }, this));
        this.form = form;
        var dims = getViewportDimensions();
        var vPos = getViewportPosition();
        setStyle(this.framework, {'z-index':'1','display':'block'});
        var bdims = getElementDimensions(this.framework);
        setStyle(this.framework, {'z-index':'10002','display':'none'});
        map(function(menu) {setStyle(menu, {'z-index':'3000'})}, 
            concat($$('.menu'), $$('.littlemenu'), $$('#messageSlot')));
        setElementDimensions(this.dimbg, getViewportDimensions());
        setElementPosition(this.dimbg, getViewportPosition());
        setStyle(this.box, {'position':'relative'});
        setElementPosition(this.framework, {
            x:((dims.w+vPos.x)/2)-(bdims.w/2),
            y:((dims.h/2)+vPos.y)-(bdims.h/2)
        });
        this.moveBox('front');
        connect('dialog_close','onclick',function(){$('dialog').hide()});
        var d2 = this.lock.acquire(); 
        d2.addCallback(bind(function() {
            try {
                connect('new_id','onkeyup', captureSubmit);
            } catch(e) { noop(); }
            this.lock.release();
        }, this));
        appear(this.dimbg, {duration:0.1, from:0.0, to:0.7});
        showElement(this.box);
        showElement(this.framework);
    },
    hide: function() {
        fade(this.dimbg, {duration:0.1});
        this.box.innerHTML = this.defaultContent;
        hideElement(this.framework);
        this.moveBox('back');
        if (this.lock.locked) this.lock.release();
    },
    fetch: function(url) {
        var urlsplit = url.split('/');
        var id = urlsplit[urlsplit.length-1];
        var d = doSimpleXMLHttpRequest(url);
        d.addCallback(method(this, function(req){this.fill(id, req)}));
    },
    fill: function(dialogid, request) {
        $('dialog_innercontent').innerHTML = request.responseText;
        forEach(this.loadEvents[dialogid], function(f){f()});
        var elements = getFormElements($('dialog_innercontent'));
        var first = elements[0];
        var textboxes = elements[1];
        var submits = elements[2];
        var submt = submits[0];
        var connectTextboxes = function(box) {
            connect(box, 'onkeyup', function(e){
                if (e.key().string=='KEY_ENTER') submt.click();
            });
        }
        if (submits.length==1) map(connectTextboxes, textboxes);
        first.focus();
        if (this.lock.locked) this.lock.release();
    },
    submit_form: function(action, formname) {
        var f = formname?document.forms[formname]:(this.form?this.form:$('proxy_form'));
        setStyle(this.box, {'z-index':'-1'});
        this.box = removeElement(this.box);
        if (action != '') f.action = action;
        f.appendChild(this.box);
        return true;
    },
    submit_form_and_check: function(action, formname, prep_id) {
        var errmsg = $('errmsg');
        var input = $('new_id');
        var label = $('new_id_label');
        var new_id = escape(input.value);
        var submit = $('dialog_submit');
        var path = $('checkValidIdPath').value
        var myform = formname?document.forms[formname]:this.form;
        errmsg.innerHTML = "";
        Morph(input, {"style": {"color": "black"}});
        Morph(label, {"style": {"color": "white"}});
        var d = doSimpleXMLHttpRequest(path+'/checkValidId',
            {'id':new_id, 'prep_id':prep_id});

        d.addCallback(bind(function (r) { 
            if (r.responseText == 'True') { 
                var f = formname?document.forms[formname]:
                    (this.form?this.form:$('proxy_form'));
                setStyle(this.box, {'z-index':'-1'});
                this.box = removeElement(this.box);
                if (action != '') f.action = action;
                f.appendChild(this.box);
                submit.onclick = ""
                submit.click();
            } else {
                Morph(input, {"style": {"color": "red"}});
                Morph(label, {"style": {"color": "red"}});
                errmsg.innerHTML = r.responseText;
                shake(input);
                shake(label);
                shake(errmsg);
            }
        }, this));
    }
}

log("Dialog javascript loaded.")
