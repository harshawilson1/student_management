    function toggleSidebar() {
        const sidebar = document.getElementById("sidebar");
        const main = document.getElementById("main");
        sidebar.classList.toggle("active");
        main.classList.toggle("active");
    }