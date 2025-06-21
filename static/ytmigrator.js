$(function () {
  for (btn of $(".btn")) {
    mdc.ripple.MDCRipple.attachTo(btn);
  }

  for (field of $(".mdc-text-field")) {
    mdc.textField.MDCTextField.attachTo(field);
  }

  for (box of $(".mdc-checkbox")) {
    mdc.checkbox.MDCCheckbox.attachTo(box);
  }

  for (form of $(".mdc-form-field")) {
    mdc.formField.MDCFormField.attachTo(form);
  }

  function collapse(event) {
    $(event.target).parent().next().toggleClass("hidden-item");
    if ($(event.target).text() == "expand_less") {
      $(event.target).text("expand_more");
    } else {
      $(event.target).text("expand_less");
    }
  }

  for (let list of $(".mdc-list-group").children()) {
    if ($(list).children().length == 0) {
      $(list).parent().prev().remove();
      $(list).parent().remove();
    }
  }

  if ($("#list-categories").children().length == 0) {
    $("#list-categories").remove();
    $("#import-suggest")[0].classList.remove("hidden-item");
  }

  $(".collapse-btn").click(collapse);

  let topBarRegular = $(".mdc-top-app-bar--regular")[0];
  let topBarContextual = $(".mdc-top-app-bar--contextual")[0];

  function boxCheckCount() {
    let checkboxCount = $("#list-categories").find("input:checkbox:checked")
      .length;
    $(".mdc-top-app-bar__title").text(checkboxCount.toString() + " selected");
    if (checkboxCount > 0) {
      topBarRegular.classList.add("hidden-item");
      topBarContextual.classList.remove("hidden-item");
    } else {
      topBarContextual.classList.add("hidden-item");
      topBarRegular.classList.remove("hidden-item");
    }
  }

  for (box of $(".selection-checkbox")) {
    $(box).on("click", boxCheckCount);
  }

  function deselect_all() {
    $(".mdc-checkbox--selected")
      .find('input[type="checkbox"]:not(:disabled)')
      .prop("checked", false);
    topBarContextual.classList.add("hidden-item");
    topBarRegular.classList.remove("hidden-item");
  }

  $("#deselect_all").on("click", deselect_all);

  let drawer = mdc.drawer.MDCDrawer.attachTo(
    document.querySelector(".mdc-drawer")
  );
  let topAppBar = mdc.topAppBar.MDCTopAppBar.attachTo(
    document.getElementById("app-bar")
  );
  topAppBar.setScrollTarget(document.getElementById("main-content"));
  topAppBar.listen("MDCTopAppBar:nav", () => {
    drawer.open = !drawer.open;
  });

  let menu = new mdc.menu.MDCMenu(document.querySelector(".mdc-menu"));

  $("#menu-btn").on("click", () => {
    menu.open = true;
  });

  $("#select-all-btn").on("click", () => {
    $("input:checkbox:not(:checked)").prop("checked", true);
    boxCheckCount();
  });

  let delAccDialog = new mdc.dialog.MDCDialog(
    document.querySelector("#del-acc-dialog")
  );
  $("#del-acc-btn").click(() => {
    delAccDialog.open();
  });

  let delSelDialog = new mdc.dialog.MDCDialog(
    document.querySelector("#delete-sel-dialog")
  );
  function delSelOpen() {
    $("#selections").attr("action", "/delete");
    delSelDialog.open();
  }
  $("#delete-sel-shortcut").click(delSelOpen);
  $("#delete-sel-btn").click(delSelOpen);

  let importOauthDialog = new mdc.dialog.MDCDialog(
    document.querySelector("#import-oauth-dialog")
  );
  let importFormDialog = new mdc.dialog.MDCDialog(
    document.querySelector("#import-form-dialog")
  );
  function importPopup() {
    window.open("/auth/google/signin", "authURL", "width=400,height=600");

    importOauthDialog.open();
  }
  $("#import-more-btn").click(importPopup);
  $("#import-suggest-btn").click(importPopup);
  $("#import-oauth-next-btn").click(() => {
    importOauthDialog.close();
    importFormDialog.open();
  });
  let exportChoiceDialog = new mdc.dialog.MDCDialog(
    document.querySelector("#export-choice-dialog")
  );
  function exportChoicePopup() {
    exportChoiceDialog.open();
  }
  $("#export-sel-btn").click(exportChoicePopup);
  $("#export-sel-shortcut").click(exportChoicePopup);
  let downloadDialog = new mdc.dialog.MDCDialog(
    document.querySelector("#download-dialog")
  );
  $("#download-choice-btn").click(() => {
    $("#selections").attr("action", "/download-json");
    exportChoiceDialog.close();
    downloadDialog.open();
  });
  let exportOauthDialog = new mdc.dialog.MDCDialog(
    document.querySelector("#export-oauth-dialog")
  );
  $("#export-choice-btn").click(() => {
    exportChoiceDialog.close();
    window.open("/auth/google/signin", "authURL", "width=400,height=600");

    exportOauthDialog.open();
  });
  let exportFormDialog = new mdc.dialog.MDCDialog(
    document.querySelector("#export-form-dialog")
  );
  $("#export-oauth-next-btn").click(() => {
    exportOauthDialog.close();
    $("#selections").attr("action", "/export");
    exportFormDialog.open();
  });
});
