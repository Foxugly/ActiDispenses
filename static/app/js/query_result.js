function downloadJsonExport(filename, rows) {
    const blob = new Blob([JSON.stringify(rows, null, 2)], {type: "application/json;charset=utf-8"});
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${filename}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
}

function buildJsonRows(dt, columns) {
    return dt.rows({search: "applied", order: "applied"}).data().toArray().map(row =>
        Object.fromEntries(columns.map((column, index) => [column, row[index] ?? ""]))
    );
}

document.addEventListener("DOMContentLoaded", () => {
    const config = window.queryResultsTableConfig;
    if (!config) {
        return;
    }

    const table = document.getElementById(config.tableId);
    if (!table || !config.columns?.length) {
        document.getElementById(config.toggleButtonId)?.classList.add("d-none");
        return;
    }

    const visible = loadDataTableVisibleState(config.tableId, config.defaultVisible);
    const dt = initExportableDataTable(`#${config.tableId}`, config.filename, {
        visibleArray: visible,
        order: [0, "asc"],
        orderCellsTop: true,
        extraButtons: [
            {
                text: "JSON",
                action: () => downloadJsonExport(config.filename, buildJsonRows(dt, config.columns)),
            },
        ],
    });

    addColumnFilters(dt, config.tableId);
    bindOutsidePanelClose(config.panelId, config.toggleButtonId);

    document.getElementById(config.toggleButtonId)?.addEventListener("click", () => toggleDataTablePanel(config.panelId));
    document.getElementById(config.closeButtonId)?.addEventListener("click", () => hideDataTablePanel(config.panelId));

    const checklist = buildColumnsChecklist({
        dt,
        cols: config.columns,
        checklistId: config.checklistId,
        tableId: config.tableId,
        defaultVisible: config.defaultVisible,
    });

    document.getElementById(config.resetButtonId)?.addEventListener("click", checklist.reset);
});
