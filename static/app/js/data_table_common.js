function dataTableStorageKey(tableId) {
    return `dt_colvis_${tableId}`;
}

function loadDataTableVisibleState(tableId, fallbackArray) {
    try {
        const raw = localStorage.getItem(dataTableStorageKey(tableId));
        if (!raw) return fallbackArray;
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed) || parsed.length !== fallbackArray.length) return fallbackArray;
        return parsed.map(Boolean);
    } catch (error) {
        return fallbackArray;
    }
}

function saveDataTableVisibleState(tableId, visibleArray) {
    localStorage.setItem(dataTableStorageKey(tableId), JSON.stringify(visibleArray));
}

function findDataTableColIndex(cols, name) {
    const lowerName = String(name).toLowerCase();
    const index = cols.findIndex(col => String(col).toLowerCase() === lowerName);
    return index >= 0 ? index : null;
}

function toggleDataTablePanel(panelId) {
    document.getElementById(panelId)?.classList.toggle("d-none");
}

function hideDataTablePanel(panelId) {
    document.getElementById(panelId)?.classList.add("d-none");
}

function bindOutsidePanelClose(panelId, buttonId) {
    document.addEventListener("click", event => {
        const panel = document.getElementById(panelId);
        const button = document.getElementById(buttonId);
        if (panel && button && !panel.classList.contains("d-none") && !panel.contains(event.target) && !button.contains(event.target)) {
            hideDataTablePanel(panelId);
        }
    });
}

function buildColumnsChecklist({dt, cols, checklistId, tableId, defaultVisible}) {
    const container = document.getElementById(checklistId);
    if (!container) {
        return {reset: () => {}};
    }

    container.innerHTML = "";

    function currentVisibleArray() {
        return cols.map((_, index) => dt.column(index).visible());
    }

    cols.forEach((name, index) => {
        const checked = dt.column(index).visible();
        const colDiv = document.createElement("div");
        colDiv.className = "col-12 col-md-6 col-lg-4";
        colDiv.innerHTML = `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="${tableId}_col_${index}" ${checked ? "checked" : ""}>
                <label class="form-check-label small" for="${tableId}_col_${index}">${name}</label>
            </div>
        `;
        const input = colDiv.querySelector("input");
        input.addEventListener("change", () => {
            dt.column(index).visible(input.checked);
            saveDataTableVisibleState(tableId, currentVisibleArray());
        });
        container.appendChild(colDiv);
    });

    return {
        reset: () => {
            defaultVisible.forEach((visible, index) => dt.column(index).visible(visible));
            saveDataTableVisibleState(tableId, defaultVisible.slice());
            buildColumnsChecklist({dt, cols, checklistId, tableId, defaultVisible});
        },
    };
}

function initExportableDataTable(selector, filename, options = {}) {
    const {
        visibleArray = [],
        order = [0, "desc"],
        pageLength = 10,
        lengthMenu = [10, 25, 50, 100],
        columnDefs = [],
        orderCellsTop = false,
    } = options;

    const visibilityDefs = visibleArray.map((visible, index) => ({targets: index, visible}));
    return new DataTable(selector, {
        responsive: true,
        pageLength,
        lengthMenu,
        order: [order],
        layout: {
            topStart: {
                buttons: [
                    {extend: "copyHtml5", text: "Copier"},
                    {extend: "csvHtml5", text: "CSV", filename},
                    {extend: "excelHtml5", text: "Excel", filename},
                    {extend: "pdfHtml5", text: "PDF", filename},
                    {extend: "print", text: "Imprimer"},
                ],
            },
            topEnd: "search",
            bottomStart: ["info", "pageLength"],
            bottomEnd: "paging",
        },
        columnDefs: [...visibilityDefs, ...columnDefs],
        orderCellsTop,
    });
}

function addColumnFilters(dt, tableId) {
    const table = document.getElementById(tableId);
    const filterInputs = table?.querySelectorAll("thead tr:nth-child(2) input.column-filter") || [];
    filterInputs.forEach((input, index) => {
        input.addEventListener("input", () => {
            dt.column(index).search(input.value).draw();
        });
        input.addEventListener("click", event => event.stopPropagation());
    });
}
