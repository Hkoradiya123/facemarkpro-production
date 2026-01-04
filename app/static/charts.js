// charts.js

// Store chart instances globally
let chartInstances = {};

// Function to initialize all charts
function initializeCharts() {
    // 1. Bar Chart: Today's Attendance by Class
    const attendanceBarCtx = document.getElementById("attendanceBarChart")?.getContext('2d');
    if (attendanceBarCtx) {
        if (chartInstances.attendanceBar) {
            chartInstances.attendanceBar.destroy();
        }
        chartInstances.attendanceBar = new Chart(attendanceBarCtx, {
            type: "bar",
            data: {
                labels: ["Class A", "Class B", "Class C", "Class D"],
                datasets: [
                    {
                        label: "Present Students",
                        data: [28, 32, 26, 30],
                        backgroundColor: "#4e79a7",
                        borderRadius: 6,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 800,
                },
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        enabled: true,
                    },
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "Class",
                        },
                    },
                    y: {
                        title: {
                            display: true,
                            text: "Number of Students",
                        },
                        beginAtZero: true,
                    },
                },
            },
        });
    }

    // 2. Line Chart: Monthly Attendance Trend
    const monthlyTrendCtx = document.getElementById("monthlyAttendanceTrendChart")?.getContext('2d');
    if (monthlyTrendCtx) {
        if (chartInstances.monthlyTrend) {
            chartInstances.monthlyTrend.destroy();
        }
        chartInstances.monthlyTrend = new Chart(monthlyTrendCtx, {
            type: "line",
            data: {
                labels: ["Week 1", "Week 2", "Week 3", "Week 4"],
                datasets: [
                    {
                        label: "Attendance %",
                        data: [92, 85, 88, 94],
                        borderColor: "#f28e2c",
                        backgroundColor: "rgba(242, 142, 44, 0.2)",
                        fill: true,
                        tension: 0.4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 1000,
                },
                plugins: {
                    legend: {
                        display: true,
                    },
                    tooltip: {
                        mode: "index",
                        intersect: false,
                    },
                },
                interaction: {
                    mode: "nearest",
                    axis: "x",
                    intersect: false,
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: "Attendance %",
                        },
                    },
                    x: {
                        title: {
                            display: true,
                            text: "Week",
                        },
                    },
                },
            },
        });
    }

    // 3. Heatmap: Subject vs Classroom Matrix
    const heatmapCtx = document.getElementById("subjectClassroomHeatmap")?.getContext('2d');
    if (heatmapCtx) {
        if (chartInstances.heatmap) {
            chartInstances.heatmap.destroy();
        }
        chartInstances.heatmap = new Chart(heatmapCtx, {
            type: "matrix",
            data: {
                datasets: [
                    {
                        label: "Subject-Classroom Attendance",
                        data: [
                            { x: "Math", y: "CR1", v: 85 },
                            { x: "Physics", y: "CR1", v: 92 },
                            { x: "Chemistry", y: "CR2", v: 78 },
                            { x: "English", y: "CR2", v: 88 },
                        ],
                        backgroundColor(context) {
                            const value = context.dataset.data[context.dataIndex].v;
                            const alpha = value / 100;
                            return `rgba(70, 130, 180, ${alpha})`;
                        },
                        borderColor: "#ffffff",
                        borderWidth: 1,
                        width: ({ chart }) => chart.chartArea.width / 5,
                        height: ({ chart }) => chart.chartArea.height / 5,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        callbacks: {
                            title: (ctx) => `${ctx[0].raw.y} - ${ctx[0].raw.x}`,
                            label: (ctx) => `Attendance: ${ctx.raw.v}%`,
                        },
                    },
                },
                scales: {
                    x: {
                        type: "category",
                        labels: ["Math", "Physics", "Chemistry", "English"],
                        offset: true,
                    },
                    y: {
                        type: "category",
                        labels: ["CR1", "CR2"],
                        offset: true,
                    },
                },
            },
            plugins: [ChartMatrix.MatrixController],
        });
    }
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
});

// Reinitialize charts when layout changes
window.addEventListener('resize', function() {
    initializeCharts();
});

// Export the initialization function
window.initializeCharts = initializeCharts;
