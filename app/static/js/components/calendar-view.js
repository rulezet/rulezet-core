/**
 * calendar-view.js — a calendar (month / week / day / list) usable anywhere, on top of FullCalendar
 * (MIT, https://fullcalendar.io), loaded once from the CDN at a pinned version.
 *
 * Props:
 *   events       [{ id, title, start, end?, allDay?, color?, editable?, classNames?, extendedProps? }]
 *   view         first view: 'dayGridMonth' (default) | 'timeGridWeek' | 'timeGridDay' | 'listWeek'
 *   editable     events can be dragged to another day / time (each event can still say editable: false)
 *   selectable   a day / a time range can be clicked or swept
 *   droppable    elements made draggable with makeDraggable() can be dropped on it
 *   height       CSS height or 'auto' (default)
 *   firstDay     0 = Sunday, 1 = Monday (default)
 *
 * Emits:
 *   range        ({ start, end })        the visible dates changed — fetch the events for them
 *   select       ({ start, end, allDay }) a day or a time range was picked
 *   event-click  ({ event, el })         event = { id, title, start, extendedProps }
 *   event-drop   ({ event, start, delta, revert })  call revert() to put it back
 *   drop         ({ date, allDay, el })  an external draggable was dropped
 *
 * Exposed (ref): makeDraggable(containerEl, itemSelector) — the matching elements in the container can
 *   be dragged onto the calendar ('drop' gives the element back: put what you need on its dataset);
 *   gotoDate(date), changeView(view).
 *
 * CSS: css/components/calendar-view.css (theme variables, dark mode).
 */
const { ref, onMounted, onBeforeUnmount, watch } = Vue;

const FC_URL = 'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js';
let fcPromise = null;
function loadFullCalendar() {
    if (window.FullCalendar) return Promise.resolve(window.FullCalendar);
    if (!fcPromise) {
        fcPromise = new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = FC_URL;
            s.onload = () => resolve(window.FullCalendar);
            s.onerror = () => { fcPromise = null; reject(new Error('FullCalendar could not be loaded')); };
            document.head.appendChild(s);
        });
    }
    return fcPromise;
}

export default {
    name: 'CalendarView',
    props: {
        events: { type: Array, default: () => [] },
        view: { type: String, default: 'dayGridMonth' },
        editable: { type: Boolean, default: false },
        selectable: { type: Boolean, default: false },
        droppable: { type: Boolean, default: false },
        height: { type: String, default: 'auto' },
        firstDay: { type: Number, default: 1 },
    },
    emits: ['range', 'select', 'event-click', 'event-drop', 'drop'],
    setup(props, { emit, expose }) {
        const el = ref(null);
        const failed = ref(false);
        let calendar = null;
        const draggables = [];

        // While something is dragged (a workflow from outside, or an event), the cell under the pointer
        // gets a blue outline — "it will go here". FullCalendar alone only shows that for its own events.
        let marked = [];
        function clearMark() { marked.forEach(m => m.classList.remove('cv-drop-target', 'cv-drop-slot')); marked = []; }
        function markAt(x, y) {
            clearMark();
            const stack = document.elementsFromPoint(x, y);
            const day = stack.map(n => n.closest && n.closest('.fc-daygrid-day, .fc-timegrid-col')).find(Boolean);
            if (!day || !el.value || !el.value.contains(day)) return;
            day.classList.add('cv-drop-target');
            marked.push(day);
            const slot = stack.map(n => n.closest && n.closest('.fc-timegrid-slot-lane')).find(Boolean);
            if (slot) { slot.classList.add('cv-drop-slot'); marked.push(slot); }
        }
        const onMove = (e) => { const p = e.touches ? e.touches[0] : e; if (p) markAt(p.clientX, p.clientY); };
        function startTracking() {
            document.addEventListener('mousemove', onMove);
            document.addEventListener('touchmove', onMove, { passive: true });
            document.addEventListener('mouseup', stopTracking, { once: true });
            document.addEventListener('touchend', stopTracking, { once: true });
        }
        function stopTracking() {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('touchmove', onMove);
            setTimeout(clearMark, 0);
        }

        const plain = (ev) => ({ id: ev.id, title: ev.title, start: ev.start, end: ev.end, allDay: ev.allDay,
                                 extendedProps: { ...ev.extendedProps } });

        onMounted(async () => {
            let FC;
            try { FC = await loadFullCalendar(); } catch { failed.value = true; return; }
            calendar = new FC.Calendar(el.value, {
                initialView: props.view,
                firstDay: props.firstDay,
                height: props.height,
                nowIndicator: true,
                dayMaxEvents: 4,
                editable: props.editable,
                selectable: props.selectable,
                droppable: props.droppable,
                eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
                slotLabelFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
                headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek' },
                buttonText: { today: 'Today', month: 'Month', week: 'Week', day: 'Day', list: 'List' },
                events: props.events,
                datesSet: (info) => emit('range', { start: info.start, end: info.end }),
                select: (info) => { emit('select', { start: info.start, end: info.end, allDay: info.allDay }); calendar.unselect(); },
                eventClick: (info) => { info.jsEvent.preventDefault(); emit('event-click', { event: plain(info.event), el: info.el }); },
                eventDrop: (info) => emit('event-drop', { event: plain(info.event), start: info.event.start,
                                                          delta: info.delta, revert: info.revert }),
                drop: (info) => { clearMark(); emit('drop', { date: info.date, allDay: info.allDay, el: info.draggedEl }); },
                eventDragStart: () => startTracking(),
                eventDragStop: () => stopTracking(),
            });
            calendar.render();
        });

        watch(() => props.events, (events) => {
            if (!calendar) return;
            calendar.removeAllEvents();
            calendar.addEventSource(events);
        });

        async function makeDraggable(container, itemSelector) {
            if (!container) return;
            const FC = await loadFullCalendar().catch(() => null);
            if (!FC) return;
            const begin = (e) => { if (e.target.closest(itemSelector) && !e.target.closest('input, button')) startTracking(); };
            container.addEventListener('mousedown', begin);
            container.addEventListener('touchstart', begin, { passive: true });
            draggables.push(new FC.Draggable(container, {
                itemSelector,
                eventData: (item) => ({ title: item.dataset.title || '', duration: '01:00', create: false }),
            }));
        }
        function gotoDate(d) { if (calendar) calendar.gotoDate(d); }
        function changeView(v) { if (calendar) calendar.changeView(v); }

        expose({ makeDraggable, gotoDate, changeView, ready: () => !!calendar });
        onBeforeUnmount(() => { stopTracking(); draggables.forEach(d => d.destroy()); if (calendar) calendar.destroy(); });

        return { el, failed };
    },
    template: `
    <div class="calendar-view">
        <div v-if="failed" class="calendar-view__error"><i class="fa-solid fa-triangle-exclamation me-1"></i>The calendar could not be loaded (no access to cdn.jsdelivr.net?).</div>
        <div ref="el"></div>
    </div>`,
};
