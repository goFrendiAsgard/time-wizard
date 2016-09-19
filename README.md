# Time Wizard

Kanban, Pomodoro, and task reminder for Tmux user

![Time Wizard](goFrendiAsgard.github.com/time-wizard/time-wizard.jpg)

##KANBAN & POMODORO

* time-wizard.py kanban
* time-wizard.py pomodoro

##CONFIGURATION

* time-wizard.py show-config
* time-wizard.py edit-config key:value

##BOARDS

* time-wizard.py show-board
* time-wizard.py add-board name:board-name
* time-wizard.py edit-board id:board-id, key:board-name
* time-wizard.py delete-board id:board-id

##TASKS

* time-wizard.py show-task
* time-wizard.py add-task key:value, key:value,...
* time-wizard.py edit-task id:task-id, key:value,...
* time-wizard.py delete-task id:task-id

__Available Keys for Tasks :__ name, board, remind_on, remind_for

You can use following string formats for `remind_for`:

* `Tuesday 18:00` which will remind you every Tuesday at 18:00
* `2016-05-26 17:00` which will remind you on May,26, 2016 at 17:00
* `18:00` which will remind you everyday at 18:00
