import { apiRequest } from "./api.js";
import { spaceApiRequest } from "./spaceApi.js";


function querySuffix(params = {}) {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
        if (
            value !== undefined &&
            value !== null &&
            value !== ""
        ) {
            query.set(key, value);
        }
    });

    return query.size ? `?${query.toString()}` : "";
}


export function getCalendarSettings() {
    return spaceApiRequest("/api/calendar/settings");
}


export function updateCalendarSettings(data) {
    return spaceApiRequest("/api/calendar/settings", {
        method: "PUT",
        body: JSON.stringify(data)
    });
}


export function listCalendarEntries() {
    return spaceApiRequest("/api/calendar/entries");
}


export function createCalendarEntry(data) {
    return spaceApiRequest("/api/calendar/entries", {
        method: "POST",
        body: JSON.stringify(data)
    });
}


export function updateCalendarEntry(entryId, data) {
    return spaceApiRequest(
        `/api/calendar/entries/${encodeURIComponent(entryId)}`,
        {
            method: "PATCH",
            body: JSON.stringify(data)
        }
    );
}


export function deleteCalendarEntry(entryId) {
    return spaceApiRequest(
        `/api/calendar/entries/${encodeURIComponent(entryId)}`,
        { method: "DELETE" }
    );
}


export function listCalendarSeries() {
    return spaceApiRequest("/api/calendar/series");
}


export function createCalendarSeries(data) {
    return spaceApiRequest("/api/calendar/series", {
        method: "POST",
        body: JSON.stringify(data)
    });
}


export function updateCalendarSeries(seriesId, data) {
    return spaceApiRequest(
        `/api/calendar/series/${encodeURIComponent(seriesId)}`,
        {
            method: "PATCH",
            body: JSON.stringify(data)
        }
    );
}


export function deleteCalendarSeries(seriesId) {
    return spaceApiRequest(
        `/api/calendar/series/${encodeURIComponent(seriesId)}`,
        { method: "DELETE" }
    );
}


export function listCalendarOccurrences(startDate, endDate) {
    return spaceApiRequest(
        `/api/calendar/occurrences${querySuffix({
            start_date: startDate,
            end_date: endDate
        })}`
    );
}


export function listMembers() {
    return spaceApiRequest("/api/members");
}


export function listPeople() {
    return apiRequest("/api/people");
}


export function createCalendarSeriesExclusion(seriesId, excludedDate) {
    return spaceApiRequest(
        `/api/calendar/series/${encodeURIComponent(seriesId)}/exclusions`,
        {
            method: "POST",
            body: JSON.stringify({
                excludedDate
            })
        }
    );
}


export function deleteCalendarSeriesExclusion(seriesId, excludedDate) {
    return spaceApiRequest(
        `/api/calendar/series/${encodeURIComponent(seriesId)}/exclusions/` +
        encodeURIComponent(excludedDate),
        { method: "DELETE" }
    );
}
