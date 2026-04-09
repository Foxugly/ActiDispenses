async function downloadWsSql(button) {
    const text = document.getElementById("btnText");
    const spinner = document.getElementById("btnSpinner");
    button.disabled = true;
    text.classList.add("d-none");
    spinner.classList.remove("d-none");

    try {
        const response = await fetch(button.dataset.downloadUrl);
        if (!response.ok) {
            throw new Error("Server error");
        }
        const disposition = response.headers.get("Content-Disposition");
        let filename = "download.txt";
        if (disposition && disposition.includes("filename=")) {
            filename = disposition.split("filename=")[1].replace(/["']/g, "");
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        alert("Erreur lors de la generation du fichier.");
    }

    button.disabled = false;
    spinner.classList.add("d-none");
    text.classList.remove("d-none");
}

document.addEventListener("DOMContentLoaded", () => {
    const table = document.querySelector("#tblWs");
    const sqlButton = document.getElementById("sqlBtn");
    const config = window.wsIssueTableConfig || null;

    if (sqlButton?.dataset.downloadUrl) {
        sqlButton.addEventListener("click", () => downloadWsSql(sqlButton));
    }

    if (!table || !config?.columns?.length) {
        document.getElementById("btnColsWs")?.classList.add("d-none");
        return;
    }

    const visible = loadDataTableVisibleState(config.tableId, config.defaultVisible);
    const sortIndex = findDataTableColIndex(config.columns, "timestampsent") ?? findDataTableColIndex(config.columns, "dt_creation") ?? 0;
    const dtWs = initExportableDataTable(`#${config.tableId}`, config.filename, {
        visibleArray: visible,
        order: [sortIndex, "desc"],
    });

    bindOutsidePanelClose(config.panelId, config.toggleButtonId);
    document.getElementById(config.toggleButtonId)?.addEventListener("click", () => toggleDataTablePanel(config.panelId));
    document.getElementById(config.closeButtonId)?.addEventListener("click", () => hideDataTablePanel(config.panelId));

    const wsChecklist = buildColumnsChecklist({
        dt: dtWs,
        cols: config.columns,
        checklistId: config.checklistId,
        tableId: config.tableId,
        defaultVisible: config.defaultVisible,
    });

    document.getElementById(config.resetButtonId)?.addEventListener("click", wsChecklist.reset);
});
