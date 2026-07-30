const DEFAULT_ROUTE = "dashboard";
let routerInitialized = false;

function getRouteFromHash() {
    const route = window.location.hash.replace("#", "").trim();
    return route || DEFAULT_ROUTE;
}

function showRoute(route) {
    const pages = document.querySelectorAll("[data-page]");
    const links = document.querySelectorAll("[data-route]");

    const matchingPage = document.querySelector(`[data-page="${route}"]`);
    const safeRoute = matchingPage ? route : DEFAULT_ROUTE;

    pages.forEach(page => {
        page.hidden = page.dataset.page !== safeRoute;
    });

    links.forEach(link => {
        const isActive = link.dataset.route === safeRoute;

        link.classList.toggle("active", isActive);

        if (isActive) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }
    });
}

export function initializeRouter() {
    if (routerInitialized) {
        return;
    }
    routerInitialized = true;

    window.addEventListener("hashchange", () => {
        showRoute(getRouteFromHash());
    });

    showRoute(getRouteFromHash());
}
