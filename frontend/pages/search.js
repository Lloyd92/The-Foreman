import { universalSearch } from "../utils/searchApi.js";


let searchInitialized = false;

const SOURCE_ROUTES = Object.freeze({
    project: "projects",
    task: "tasks",
    tool: "tools",
    inventory: "inventory",
    care_plan: "care",
    calendar_entry: "calendar",
    calendar_series: "calendar",
    money_account: "money",
    money_category: "money",
    money_transaction: "money",
    money_budget: "money",
    money_obligation: "money",
    library_record: "library"
});


function clean(value) {
    return String(value ?? "").trim();
}


export function routeForSearchResult(sourceType) {
    return SOURCE_ROUTES[sourceType] ?? null;
}


function formatSourceType(sourceType) {
    return clean(sourceType)
        .replaceAll("_", " ")
        .replace(/\b\w/g, value => value.toUpperCase());
}


function setMessage(message, isError = false) {
    const element = document.getElementById(
        "universal-search-message"
    );

    if (!element) {
        return;
    }

    element.textContent = message;
    element.classList.toggle("error", isError);
}


function renderResults(results) {
    const container = document.getElementById(
        "universal-search-results"
    );
    const empty = document.getElementById(
        "universal-search-empty"
    );

    if (!container || !empty) {
        return;
    }

    container.replaceChildren();

    for (const result of results) {
        const item = document.createElement("article");
        item.className = "search-result";

        const heading = document.createElement("div");
        heading.className = "search-result-heading";

        const title = document.createElement("h4");
        title.textContent = result.title;

        const type = document.createElement("span");
        type.textContent = formatSourceType(result.sourceType);

        heading.append(title, type);

        const summary = document.createElement("p");
        summary.textContent = result.summary || "No summary recorded.";

        const match = document.createElement("p");
        match.className = "search-result-match";
        match.textContent = `Matched: ${result.matchedText}`;

        item.append(heading, summary, match);

        const route = routeForSearchResult(result.sourceType);

        if (route) {
            const link = document.createElement("a");
            link.className = "table-action-button search-result-link";
            link.href = `#${route}`;
            link.textContent = "Open owning screen";
            item.appendChild(link);
        }

        container.appendChild(item);
    }

    empty.hidden = results.length > 0;
}


async function runSearch(form) {
    const data = new FormData(form);
    const query = clean(data.get("query"));

    if (!query) {
        renderResults([]);
        setMessage("Enter a search term.", true);
        return;
    }

    const response = await universalSearch(query);
    renderResults(response.results);
    setMessage(
        `${response.results.length} result${
            response.results.length === 1 ? "" : "s"
        } found.`
    );
}


export async function initializeSearchPresentation() {
    if (searchInitialized) {
        return {
            status: "already-initialized"
        };
    }

    searchInitialized = true;

    const form = document.getElementById("universal-search-form");

    form?.addEventListener("submit", async event => {
        event.preventDefault();

        try {
            await runSearch(form);
        } catch (error) {
            console.error("Universal Search failed:", error);
            renderResults([]);
            setMessage(
                "Universal Search is currently unavailable.",
                true
            );
        }
    });

    return {
        status: "complete"
    };
}
