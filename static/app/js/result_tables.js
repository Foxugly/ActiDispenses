document.addEventListener("DOMContentLoaded", () => {
    const configs = window.resultTablesConfig || [];

    configs.forEach(config => {
        const table = document.getElementById(config.tableId);
        if (!table || !config.columns?.length) {
            document.getElementById(config.toggleButtonId)?.classList.add("d-none");
            return;
        }

        const visible = loadDataTableVisibleState(config.tableId, config.defaultVisible);
        const sortIndex = findDataTableColIndex(config.columns, "dt_creation")
            ?? findDataTableColIndex(config.columns, "timestampsent")
            ?? 0;
        const dt = initExportableDataTable(`#${config.tableId}`, config.filename, {
            visibleArray: visible,
            order: [sortIndex, "desc"],
            orderCellsTop: true,
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
});
