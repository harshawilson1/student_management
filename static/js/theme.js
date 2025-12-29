document.addEventListener("DOMContentLoaded", function () {
    const toggleBtn = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("mySidebar");

    // Select all content wrappers
    const contentWrappers = document.querySelectorAll(".dashboard-container, .container");

    if (toggleBtn) {
        toggleBtn.addEventListener("click", function () {
            // Toggle sidebar
            sidebar.classList.toggle("open");

            // Adjust content wrapper margin
            contentWrappers.forEach(wrapper => {
                if (sidebar.classList.contains("open")) {
                    wrapper.style.marginLeft = "240px";
                } else {
                    wrapper.style.marginLeft = "0";
                }
            });
        });
    }
});
document.addEventListener('DOMContentLoaded', function() {
    // Attendance Line Chart
    const attendanceCanvas = document.getElementById('attendanceChart');
    const attendanceValues = JSON.parse(attendanceCanvas.dataset.values);
    const attendanceLabels = JSON.parse(attendanceCanvas.dataset.labels);

    new Chart(attendanceCanvas, {
        type: 'line', // Line chart
        data: {
            labels: attendanceLabels,
            datasets: [{
                label: 'Attendance (%)',
                data: attendanceValues,
                fill: true,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.3, // smooth curve
                pointRadius: 5
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Attendance %'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            }
        }
    });

    // Fees Chart (if needed)
    const feesCanvas = document.getElementById('feesChart');
    const feesValues = JSON.parse(feesCanvas.dataset.values);
    const feesLabels = JSON.parse(feesCanvas.dataset.labels);

    new Chart(feesCanvas, {
        type: 'bar',
        data: {
            labels: feesLabels,
            datasets: [{
                label: 'Fees Collected',
                data: feesValues,
                backgroundColor: 'rgba(153, 102, 255, 0.6)',
                borderColor: 'rgba(153, 102, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
});