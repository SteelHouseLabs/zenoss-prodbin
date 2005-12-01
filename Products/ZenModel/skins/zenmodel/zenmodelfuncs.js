//<script metal:define-macro="submitAction" language="JavaScript">
function submitAction(myform, url) {
    myform.action=url
    myform.submit()
}

function submitViaEnter(evt) {
    evt = (evt) ? evt : event;
    var target = (evt.target) ? evt.target : evt.srcElement;
    var form = target.form;
    var charCode = (evt.charCode) ? evt.charCode : 
        ((evt.which) ? evt.which : evt.keyCode);
    if (charCode == 13 || charCode == 3) {
        form.submit();
        return false;
    }
    return true;
}

function blockSubmitViaEnter(evt) {
    evt = (evt) ? evt : event;
    var charCode = (evt.charCode) ? evt.charCode : 
        ((evt.which) ? evt.which : evt.keyCode);
    if (charCode == 13 || charCode == 3) {
        return false;
    }
    return true;
}

//<script metal:define-macro="popupwindow" language="JavaScript">
function popupwindow(url, title, width, height) {
    windowprops = "width=" + width + ",height=" + height 
        + ",resizable=yes,scrollbars=yes";
    mywindow = window.open(url, title, windowprops);
}
