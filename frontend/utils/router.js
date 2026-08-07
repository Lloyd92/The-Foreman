const DEFAULT_ROUTE = "today";
const ROUTE_ALIASES = Object.freeze({
    dashboard: DEFAULT_ROUTE
});
const PARENT_NAV_ROUTES = Object.freeze({
    tasks: "work",
    projects: "work",
    inventory: "resources",
    mealworms: "resources",
    budget: "money",
    recovery: "settings"
});
let routerInitialized = false;

function getRouteFromHash() {
    const route = window.location.hash.replace("#", "").trim();
    return route || DEFAULT_ROUTE;
}

function canonicalizeToToday() {
    if (window.location.hash === `#${DEFAULT_ROUTE}`) {
        return;
    }

    const canonicalUrl = (
        `${window.location.pathname}${window.location.search}` +
        `#${DEFAULT_ROUTE}`
    );
    window.history.replaceState(null, "", canonicalUrl);
}

function showRoute(requestedRoute) {
    const pages = [...document.querySelectorAll("[data-page]")];
    const links = document.querySelectorAll("[data-route]");
    const route = ROUTE_ALIASES[requestedRoute] || requestedRoute;
    const matchingPage = pages.find(page => page.dataset.page === route);
    const safeRoute = matchingPage ? route : DEFAULT_ROUTE;

    if (requestedRoute !== route || !matchingPage) {
        canonicalizeToToday();
    }

    pages.forEach(page => {
        page.hidden = page.dataset.page !== safeRoute;
    });

    const activeNavRoute = PARENT_NAV_ROUTES[safeRoute] || safeRoute;

    links.forEach(link => {
        const isActive = link.dataset.route === activeNavRoute;

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
