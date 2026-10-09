# Tessaris Project Management Workspace

## Product intent

Project Management is the controlled delivery layer between a business goal and the work required to achieve it. It must support a small practical job, a client engagement, a refurbishment, an internal initiative, an R&D programme or a departmental target without forcing every user into enterprise project-management ceremony.

The distinguishing feature is Project Pilot. The workspace is not only a board of tasks: the Pilot understands the project outcome, scope, budget, people, materials, dependencies, risks, evidence and decisions. It can build and maintain the plan conversationally while every material record change remains explicit and attributable.

## Core experience

The existing split-screen department pattern remains:

- **Left: Project Pilot stream.** Conversation, explanations, suggested plans, review prompts, attachments and explicit action proposals.
- **Adjustable divider.** The user can resize the conversational and working surfaces.
- **Right: Project workspace.** An editable portfolio or selected project shown through interchangeable views.

The right side should feel like one coherent working area rather than a set of unrelated reports.

## Information architecture

### Portfolio level

1. **Overview**
   - Live projects, projects at risk, overdue work and open decisions.
   - Total budget, spent, committed and forecast-at-completion.
   - Projects requiring attention, with the reason made explicit.
   - Configurable widgets: task overview, status, owner, overdue and due-date views.
2. **Projects**
   - Searchable cards or compact rows.
   - Filters for owner, customer, type, status, priority and date.
   - New-project flow with templates and Project Pilot-assisted planning.
3. **My work**
   - Tasks, approvals and decisions assigned to the signed-in person.
4. **Portfolio timeline**
   - Major milestones and cross-project deadlines.
5. **Portfolio budget**
   - Budget, committed cost, actual cost, remaining budget and forecast.

### Selected-project level

The selected project opens beneath a persistent project header containing its title, outcome, owner, customer or sponsor, status, progress, target date and financial position.

Primary views:

1. **Table** -- editable grouped work items for fast day-to-day administration.
2. **Board** -- Kanban columns for Not started, Working, Waiting/blocked, Review and Done.
3. **Timeline** -- people- or workstream-oriented date bars without dependency links.
4. **Gantt** -- tasks and milestones with dependencies, critical path and baseline comparison.
5. **Calendar** -- deadline and milestone calendar.
6. **Dashboard** -- delivery, owner, deadline, budget and risk widgets.
7. **Files & evidence** -- briefs, quotes, photos, drawings, deliverables and approvals attached to the relevant record.
8. **Activity & decisions** -- append-only change history, status updates and decision log.

The first release should expose **Table, Board, Timeline and Dashboard**. Gantt, Calendar and Files & evidence should follow once the underlying dependency and attachment records are complete.

## Editable work model

Every work item should support:

- title and description;
- status and priority;
- owner and collaborators;
- start date, due date and optional duration;
- project phase or workstream;
- milestone flag;
- predecessor and dependency type;
- estimated hours or effort;
- estimated, committed and actual cost;
- customer-visible versus internal classification;
- checklist/subtasks;
- attachments and linked evidence;
- comments and updates;
- approval requirement;
- completion evidence and completed-at timestamp.

Rows should be edited inline. Selecting a row opens a right-side detail drawer rather than navigating away from the project.

## Project creation

The user can create a project manually or ask Project Pilot. The minimum viable brief is:

- intended outcome;
- project type;
- accountable owner;
- customer or sponsor;
- target date;
- currency and budget.

Project Pilot can propose:

- phases and milestones;
- work items and dependencies;
- likely roles, people, suppliers, materials and equipment;
- a starting budget allocation and contingency;
- initial risks and required decisions;
- an evidence/approval boundary.

The proposal is shown as a reviewable plan. Nothing is written until the user accepts the proposed actions. The user can accept all, edit individual actions or reject them.

Useful starting templates:

- client delivery;
- construction/refurbishment;
- professional-services engagement;
- software or product implementation;
- internal improvement programme;
- research and development;
- department target;
- simple job or event.

## Project Pilot intelligence

Project Pilot must operate from the same canonical records shown in the workspace. It should:

- convert natural-language outcomes into a structured project proposal;
- answer factual questions from current project evidence;
- produce daily or weekly status summaries;
- identify overdue work, missing owners, broken dependencies and milestone risk;
- distinguish a recorded fact from an inference or forecast;
- detect budget pressure from actual and committed costs;
- calculate forecast-at-completion and expected variance;
- identify workload collisions and missing resource coverage;
- draft customer, sponsor or team updates;
- request the smallest missing fact needed to continue;
- recommend a recovery plan when delivery slips;
- convert meeting notes, emails, quotes and uploaded documents into proposed updates;
- never silently change dates, budgets, ownership, commitments or external communications.

The Pilot should surface a small **Attention now** list rather than overwhelming the user with generic AI advice. Each alert must name the evidence, affected project and proposed next action.

## Delivery health

Health must not be a manually coloured label alone. Tessaris should derive and explain it from:

- schedule variance and overdue dependencies;
- milestone confidence;
- percentage of tasks completed, weighted by effort where available;
- budget consumed versus progress achieved;
- committed future costs;
- unresolved high-impact risks;
- blocked work and decisions awaiting approval;
- resource overload or uncovered roles;
- missing evidence for claimed completion.

The displayed state can be **On track**, **Needs attention**, **At risk**, **Blocked** or **Complete**. A human may override it, but the override and reason are recorded.

## Financial control

Project financials should separate:

- approved budget;
- contingency;
- planned/estimated cost;
- committed cost such as accepted supplier quotes;
- actual paid or incurred cost;
- invoiced/recoverable amount for client work;
- forecast-at-completion;
- forecast variance;
- remaining uncommitted budget.

Finance remains the canonical accounting source. Project Management holds the operational allocation and links to accepted Finance evidence; it must not create a second unofficial ledger.

## People and capacity

Project members should link to the People department rather than use free text once a person record exists. The project should show role, authority, allocation, availability and conflicts. External contractors and suppliers remain distinguishable from employees.

The initial release needs assignment and simple capacity indicators. Detailed time tracking, timesheets and utilisation forecasting can follow later.

## Interaction design

### Persistent project header

- project switcher and favourite/recent projects;
- project title and outcome;
- status, owner and target date;
- progress and financial health;
- New task button;
- Ask Project Pilot action;
- filter, search and saved-view controls.

### Table view

- grouped by phase/workstream by default;
- sticky item-name column;
- columns for owner, status, priority, dates, dependency and cost;
- inline editing and keyboard navigation;
- add row and add group controls;
- compact summary footer for counts and totals.

### Board view

- status columns with counts;
- compact task cards containing owner, due date, priority and blocker indicator;
- drag-and-drop proposes a status change and records it when accepted;
- WIP pressure is visible without forcing formal WIP limits in the first release.

### Timeline view

- left rail groups by owner, phase or workstream;
- horizontal date scale with Today marker;
- draggable bars with explicit save/undo;
- milestone diamonds;
- zoom by week/month/quarter.

### Dashboard

Start with five selectable widgets:

- task overview;
- tasks by status;
- tasks by owner;
- overdue tasks;
- tasks and milestones by due date.

Then add budget burn, risk matrix, milestone confidence, team capacity and forecast variance.

## Controlled actions and auditability

All material mutations must include workspace, project, actor, time, previous value, new value and source. Sensitive actions require confirmation:

- changing an approved budget or target date;
- marking a milestone complete without required evidence;
- assigning external work;
- sending a customer or supplier message;
- accepting a quote or creating a financial commitment;
- deleting or archiving project evidence;
- closing or cancelling a project.

Undo should be available for ordinary edits. Destructive removal should be replaced by archive/restore wherever possible.

## Phased build plan

### Phase 1 -- Useful daily project workspace

- [ ] Replace report-style tabs with persistent project navigation.
- [ ] Add Table, Board, Timeline and Dashboard views.
- [ ] Add editable task fields, phases/workstreams and a task detail drawer.
- [ ] Add search, filters and saved view preferences.
- [ ] Add overdue, blocked and unassigned indicators.
- [ ] Add project templates and a structured create-project flow.
- [ ] Add configurable starter dashboard widgets.
- [ ] Preserve the split-screen Project Pilot and adjustable divider.
- [ ] Keep all views backed by one canonical project/task record.

### Phase 2 -- Project Pilot planning and supervision

- [ ] Produce structured plan proposals from a conversation.
- [ ] Add review/accept/edit/reject controls for proposed actions.
- [ ] Add evidence-grounded status summaries and Attention now.
- [ ] Add schedule, dependency, budget and resource warnings.
- [ ] Draft internal, customer and sponsor updates behind approval.
- [ ] Add daily chat date separators shared with other department streams.

### Phase 3 -- Dependencies, Gantt and evidence

- [ ] Add start dates, durations and typed dependencies.
- [ ] Add Gantt view, critical path and baseline comparison.
- [ ] Add attachment/evidence records linked to tasks and milestones.
- [ ] Add completion criteria, approval gates and completion evidence.
- [ ] Add project archive, export and reusable template creation.

### Phase 4 -- Connected business delivery

- [ ] Link project people and capacity to People.
- [ ] Link operational jobs and schedules to Operations.
- [ ] Link costs, invoices and accepted financial evidence to Finance.
- [ ] Link customer, deal and commercial scope to Sales.
- [ ] Link suppliers, quotes and materials to Procurement.
- [ ] Link client issues and handoffs to Support and Legal.

### Later, not required for the initial release

- time sheets and billable-time approval;
- advanced workload levelling;
- portfolio scenario planning;
- public client portals;
- external guest accounts;
- complex automation recipes;
- unrestricted autonomous replanning;
- full parity with specialist enterprise project-management suites.

## Acceptance criteria for the first usable release

A founder or project owner must be able to:

1. create a project in under two minutes;
2. ask Project Pilot to propose the initial work plan;
3. review and accept the proposed phases and tasks;
4. manage the same work through table, board and timeline views;
5. see who owns each task and what is late, blocked or unassigned;
6. see approved budget, spent, committed and expected remaining cost;
7. receive a concise evidence-grounded explanation of what needs attention;
8. record a decision, risk, cost or status update without leaving the project;
9. recover from an accidental ordinary edit; and
10. export a clear delivery summary without exposing private internal notes.

## Proposed default screen

```text
┌ Project coordination ───────────────────────────────────────────────────────┐
│ Project Pilot                         │ Selected project · status · owner   │
├───────────────────────┬───────────────┴─────────────────────────────────────┤
│ conversation          │ Table | Board | Timeline | Dashboard | Files       │
│                       │ Search · Person · Status · Dates · + New task       │
│ attention and         ├─────────────────────────────────────────────────────┤
│ proposed actions      │ Editable project working surface                   │
│                       │                                                     │
│                       │ Row/card selection opens a details drawer           │
│ composer + attachment │                                                     │
└───────────────────────┴─────────────────────────────────────────────────────┘
```

This keeps the speed and visual clarity of a modern work-management product while making Tessaris materially different: the working surface, department records and Project Pilot all share the same governed business context.
