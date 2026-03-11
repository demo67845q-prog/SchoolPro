/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

const CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js";
const REFRESH_INTERVAL = 60000;

class SchoolDashboard extends Component {
    static template = "SchoolDashboard";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            lastUpdated: "--:--",
            studentKpis: {
                total_students: 0, active_students: 0, new_admissions: 0,
                avg_attendance: "0.0", total_teachers: 0, total_classes: 0,
            },
            feeKpis: {
                total_invoices: 0, paid_invoices: 0, pending_invoices: 0,
                overdue_invoices: 0, total_due_amount: "0",
            },
            libraryKpis: { total_books: 0, books_issued: 0, overdue_books: 0 },
            upcomingExams: [],
            announcements: [],
        });
        this._charts = [];
        this._timer = null;

        onMounted(async () => {
            await this.loadData();
            this._timer = setInterval(() => this.loadData(), REFRESH_INTERVAL);
        });

        onWillUnmount(() => {
            if (this._timer) clearInterval(this._timer);
            this._destroyCharts();
        });
    }

    _destroyCharts() {
        this._charts.forEach(c => { try { c.destroy(); } catch(e) {} });
        this._charts = [];
    }

    async loadData() {
        this.state.loading = true;
        try { await loadJS(CHART_JS_CDN); } catch(e) {}

        const results = await Promise.allSettled([
            this._loadStudentKpis(),
            this._loadFeeKpis(),
            this._loadLibraryKpis(),
            this._loadUpcomingExams(),
            this._loadAnnouncements(),
        ]);

        if (results[0].status === "fulfilled") Object.assign(this.state.studentKpis, results[0].value);
        if (results[1].status === "fulfilled") Object.assign(this.state.feeKpis, results[1].value);
        if (results[2].status === "fulfilled") Object.assign(this.state.libraryKpis, results[2].value);
        if (results[3].status === "fulfilled") this.state.upcomingExams = results[3].value;
        if (results[4].status === "fulfilled") this.state.announcements = results[4].value;

        this.state.loading = false;
        this.state.lastUpdated = new Date().toLocaleTimeString();
        // Defer chart rendering until DOM updates
        setTimeout(() => this._renderCharts(), 100);
    }

    async _loadStudentKpis() {
        const [total, active, draft, teachers, classes] = await Promise.all([
            this.orm.searchCount("school.student", []),
            this.orm.searchCount("school.student", [["state", "=", "active"]]),
            this.orm.searchCount("school.student", [["state", "=", "draft"]]),
            this.orm.searchCount("school.teacher", [["state", "=", "active"]]),
            this.orm.searchCount("school.class", []),
        ]);
        return {
            total_students: total,
            active_students: active,
            new_admissions: draft,
            avg_attendance: "—",
            total_teachers: teachers,
            total_classes: classes,
        };
    }

    async _loadFeeKpis() {
        const [total, paid, pending, partial, overdue] = await Promise.all([
            this.orm.searchCount("school.fee.invoice", []),
            this.orm.searchCount("school.fee.invoice", [["state", "=", "paid"]]),
            this.orm.searchCount("school.fee.invoice", [["state", "=", "pending"]]),
            this.orm.searchCount("school.fee.invoice", [["state", "=", "partial"]]),
            this.orm.searchCount("school.fee.invoice", [["state", "=", "overdue"]]),
        ]);
        // Get total due amount
        let totalDue = 0;
        try {
            const dueSums = await this.orm.readGroup(
                "school.fee.invoice",
                [["state", "in", ["pending", "partial", "overdue"]]],
                ["amount_due:sum"],
                [],
            );
            totalDue = dueSums[0]?.amount_due || 0;
        } catch(e) {}

        return {
            total_invoices: total,
            paid_invoices: paid,
            pending_invoices: pending + partial,
            overdue_invoices: overdue,
            total_due_amount: Math.round(totalDue).toLocaleString(),
        };
    }

    async _loadLibraryKpis() {
        const [books, issued, overdueLib] = await Promise.all([
            this.orm.searchCount("school.library.book", [["is_active", "=", true]]),
            this.orm.searchCount("school.library.issue", [["state", "=", "issued"]]),
            this.orm.searchCount("school.library.issue", [["state", "=", "overdue"]]),
        ]);
        return { total_books: books, books_issued: issued, overdue_books: overdueLib };
    }

    async _loadUpcomingExams() {
        const exams = await this.orm.searchRead(
            "school.exam",
            [["state", "in", ["published", "ongoing", "draft"]]],
            ["name", "exam_type", "class_id", "date_start", "state"],
            { limit: 8, order: "date_start asc" }
        );
        const stateColors = {
            draft: "secondary", published: "info", ongoing: "warning",
            completed: "success", result_declared: "success",
        };
        return exams.map(e => ({
            name: e.name,
            exam_type: e.exam_type,
            class_name: e.class_id ? e.class_id[1] : "—",
            date_start: e.date_start,
            state: e.state,
            state_color: stateColors[e.state] || "secondary",
        }));
    }

    async _loadAnnouncements() {
        const anns = await this.orm.searchRead(
            "school.announcement",
            [["state", "=", "published"]],
            ["title", "audience", "priority", "date"],
            { limit: 5, order: "date desc" }
        );
        return anns.map(a => ({
            title: a.title, audience: a.audience,
            priority: a.priority, date: a.date,
        }));
    }

    _renderCharts() {
        this._destroyCharts();
        if (typeof Chart === "undefined") return;

        const studentCanvas = document.getElementById("schoolStudentChart");
        if (studentCanvas) {
            const k = this.state.studentKpis;
            const other = Math.max(0, k.total_students - k.active_students - k.new_admissions);
            this._charts.push(new Chart(studentCanvas, {
                type: "doughnut",
                data: {
                    labels: ["Active", "New Admissions", "Other"],
                    datasets: [{
                        data: [k.active_students, k.new_admissions, other],
                        backgroundColor: ["#2ecc71", "#3498db", "#95a5a6"],
                        borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: "bottom" } },
                },
            }));
        }

        const feeCanvas = document.getElementById("schoolFeeChart");
        if (feeCanvas) {
            const f = this.state.feeKpis;
            this._charts.push(new Chart(feeCanvas, {
                type: "bar",
                data: {
                    labels: ["Paid", "Pending", "Overdue"],
                    datasets: [{
                        label: "Invoices",
                        data: [f.paid_invoices, f.pending_invoices, f.overdue_invoices],
                        backgroundColor: ["#2ecc71", "#e67e22", "#e74c3c"],
                    }],
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
                },
            }));
        }
    }
}

registry.category("actions").add("school_dashboard", SchoolDashboard);
