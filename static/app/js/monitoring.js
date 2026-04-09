document.addEventListener("DOMContentLoaded", function () {
    const chartNode = document.getElementById("dailyChart");
    if (chartNode && window.monitoringDailyCounts) {
        const labels = window.monitoringDailyCounts.map(item => item.day);
        const values = window.monitoringDailyCounts.map(item => item.count);
        const ctx = chartNode.getContext("2d");

        new Chart(ctx, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Nombre de records",
                    data: values,
                    borderWidth: 1,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {display: false},
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return context.raw.toLocaleString();
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45,
                        },
                    },
                    y: {
                        type: "logarithmic",
                        beginAtZero: true,
                    },
                },
            },
        });
    }

    const abnormalTable = document.getElementById("abnormalTable");
    if (abnormalTable) {
        initExportableDataTable("#abnormalTable", "dispenses_abnormal", {
            pageLength: 25,
            order: [8, "desc"],
            columnDefs: [
                {targets: [4], className: "text-nowrap"},
                {targets: [7], width: "30%"},
                {targets: [8, 10], className: "text-nowrap"},
                {targets: [6], className: "text-end"},
            ],
        });
    }
});
