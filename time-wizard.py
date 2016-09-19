#!/usr/bin/env python
import os, re, json, time, datetime, threading, sys, termios, fcntl

#global variables
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
CONFIGURATION_FILE = os.path.join(DIR_PATH, '.time-wizard/config.json')
KANBAN_FILE = os.path.join(DIR_PATH, '.time-wizard/kanban.json')
DAYS = [
        ['mon', 'monday'], ['tue', 'tuesday'], ['wed', 'wednesday'],
        ['thu', 'thursday'], ['fri', 'friday'], ['sat', 'saturday'], ['sun', 'sunday']
    ]
DATE_SUFFIX = ['', 'st', 'nd', 'rd', 'th']
DEFAULT_CONFIGURATION = {
        'work_time' : 25 * 60,
        'rest_time' : 5 * 60,
        'sound_player' : 'canberra-gtk-play --file "%s" &> /dev/null',
        'tick_sound_file' : os.path.join(DIR_PATH, '.time-wizard/tick.ogg'),
        'alarm_sound_file' : os.path.join(DIR_PATH, '.time-wizard/alarm.ogg'),
        'switch_sound_file' : os.path.join(DIR_PATH, '.time-wizard/switch.ogg'),
        'play_tick' : True
    }
DEFAULT_KANBAN = {
        'tasks' : {},
        'boards' : {
            '1' : 'To do',
            '2' : 'Doing',
            '3' : 'Done',
            '4' : 'Scheduled'
        }
    }
DEFAULT_TASK = {
        'name' : '',
        'board': '',
        'remind_on' : '',
        'remind_for' : 30 * 60
    }

def is_string_or_unicode(value):
    return type(value) in (str, unicode)

def is_numeric(value):
    return type(value) in (float, int)

def is_list(value):
    return type(value) == list

def is_dict(value):
    return type(value) == dict

def is_valid_days_list(value):
    if is_list(value) or len(value) != 7:
        for element in value:
            if type(element) != list:
                return False
            else:
                for day in element:
                    if not is_string_or_unicode(day):
                        return False
    return True

def is_boolean_value(value):
    return value == True or value == False

def validate_dictionary(dictionary, validator, default_dictionary):
    for key in validator.keys():
        # unless I'm careless, this should not be happened. All key in validator should also be exists in default_dictionary
        if key not in default_dictionary.keys():
            default_dictionary[key] = ''
        # if dictionary[key] is invalid or not exists
        if key not in dictionary.keys() or not validator[key](dictionary[key]):
            dictionary[key] = default_dictionary[key]
    return dictionary

def generate_dictionary_id(dictionary):
    keys = [int(x) for x in dictionary.keys() if x.isdigit()]
    return max(keys)+1 if len(keys) > 0 else 1

def get_board_id(board):
    kanban = load_kanban()
    boards = kanban['boards']
    board = str(board)
    if board in boards.keys():
        return board
    else:
        board_id = [x for x in boards.keys() if boards[x] == board]
        if len(board_id) > 0:
            return str(board_id[0])
    return ''

def load_json_file(file_name, validator, default_dictionary):
    file_name = os.path.expanduser(file_name)
    # get default dictionary
    dictionary = default_dictionary
    # get dictionary from file if exists
    if os.path.exists(file_name):
        with open(file_name, "r") as infile:
            dictionary = json.load(infile)
    # validate the dictionary
    return validate_dictionary(dictionary, validator, default_dictionary)

def save_json_file(file_name, dictionary):
    with open(file_name, "w+") as outfile:
        json.dump(dictionary, outfile)


def load_configuration():
    validator = {
            'work_time' : is_numeric,
            'rest_time' : is_numeric,
            'sound_player' : is_string_or_unicode,
            'tick_sound_file' : is_string_or_unicode,
            'alarm_sound_file' : is_string_or_unicode,
            'switch_sound_file' : is_string_or_unicode,
            'play_tick' : is_boolean_value,
        }
    return load_json_file(CONFIGURATION_FILE, validator, DEFAULT_CONFIGURATION)

def load_kanban():
    validator = {
            'tasks' : is_dict,
            'boards' : is_dict
        }
    kanban = load_json_file(KANBAN_FILE, validator, DEFAULT_KANBAN)
    # boards
    for id in kanban['boards'].keys():
        val = kanban['boards'][id]
        if not is_string_or_unicode(val):
            kanban['boards'][id] = val
    # tasks
    for id in kanban['tasks'].keys():
        val = kanban['tasks'][id]
        DEFAULT_TASK = {
                'name' : is_string_or_unicode,
                'board': is_string_or_unicode,
                'remind_on' : is_string_or_unicode,
                'remind_for' : is_numeric
            }
        kanban['tasks'][id] = validate_dictionary(val, validator, DEFAULT_TASK)
    return kanban

def save_configuration(configuration):
    save_json_file(CONFIGURATION_FILE, configuration)

def save_kanban(kanban):
    save_json_file(KANBAN_FILE, kanban)

def beep(file_name):
    configuration = load_configuration()
    sound_player = configuration['sound_player']
    os.system(sound_player %(file_name,))

def tick_beep():
    configuration = load_configuration()
    file_name = configuration['tick_sound_file']
    beep(file_name)

def alarm_beep():
    configuration = load_configuration()
    file_name = configuration['alarm_sound_file']
    beep(file_name)

def switch_beep():
    configuration = load_configuration()
    file_name = configuration['switch_sound_file']
    beep(file_name)

def parse_str_timestamp_keyword(string, keyword, localtime):
    (year, mon, mday, hour, minute, sec, wday, yday, dst) = localtime
    year = str(year).rjust(4,"0")
    mon = str(mon).rjust(2,"0")
    mday = str(mday).rjust(2,"0")
    if string[:len(keyword)].lower() == keyword.lower():
        string = string.replace(keyword, "%s-%s-%s" % (year, mon, mday))
    return string

def complete_str_timestamp(string):
    localtime = time.localtime()
    (year, mon, mday, hour, minute, sec, wday, yday, dst) = localtime
    year = str(year).rjust(4,"0")
    mon = str(mon).rjust(2,"0")
    mday = str(mday).rjust(2,"0")
    # everyday, daily
    string = parse_str_timestamp_keyword(string, 'everyday', localtime)
    string = parse_str_timestamp_keyword(string, 'daily', localtime)
    # weekly (eg: every thursday, thursday, thu)
    aliases = DAYS[wday]
    for alias in aliases:
        for prefix in ('', 'every '):
            string = parse_str_timestamp_keyword(string, prefix + alias, localtime)
    # monthly (eg: every 1st, 1st, 1)
    alias = str(mday)
    for suffix in DATE_SUFFIX:
        string = parse_str_timestamp_keyword(string, alias+suffix, localtime)
    # stars
    aliases = ("*-*-*",
            "*-*-%s" % (mday),
            "*-%s-*" % (mon),
            "*-%s-%s" % (mon, mday),
            "%s-*-%s" % (year, mday),
            "%s-%s-*" % (year, mon),
            "%s-%s-%s" % (year, mon, mday)
            )
    for alias in aliases:
        string = parse_str_timestamp_keyword(string, alias, localtime)
    # ensure that string is valid date, otherwise make it empty string
    try:
        datetime.datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
        return string
    except ValueError:
        try:
            datetime.datetime.strptime(string, "%Y-%m-%d %H:%M")
            return string+":00"
        except ValueError:
            return ""

def str_to_timestamp(string):
    string = complete_str_timestamp(string)
    if string != "":
        return time.mktime(datetime.datetime.strptime(string, "%Y-%m-%d %H:%M:%S").timetuple())

def timestamp_to_str(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

def get_formatted_counter(counter):
    counter = int(counter)
    (hour, minute) = divmod(counter, 3600)
    (minute, second) = divmod(minute, 60)
    (hour, minute, second) = (str(hour).rjust(2,'0'), str(minute).rjust(2,'0'), str(second).rjust(2,'0'))
    return '%s:%s:%s' %(hour, minute, second)

'''
@input: string
@output: dictionary
@example: str_as_dictionary('name:my task, board:to do, alarm:tuesday')
'''
def str_as_dictionary(string):
    string = string.replace('"', '\\"') # escape all double quotes
    pattern = re.compile(r'\s*,\s*([a-z0-9_\-]*?)\s*:\s*')
    string = pattern.sub(r'","\1":"', "," +string)
    string = string[3:] # remove unnecessary '"",'
    string = '"' + string + '"' if string != '' else string # suround with double quote if necessary
    string = '{' + string + '}' # make it a valid json
    try:
        dictionary = json.loads(string) # turn json into dictionary
    except(ValueError):
        dictionary = {}
    for key in dictionary.keys(): # fix the type
        val = dictionary[key]
        if val.lower() == 'true':
            dictionary[key] = True
        elif val.lower() == 'false':
            dictionary[key] = False
        elif (not val.startswith('-') and val.isdigit()) or (val.startswith('-') and val[1:].isdigit()):
            dictionary[key] = int(val)
        elif val.isnumeric():
            dictionary[key] = float(val)
    return dictionary # done, return the dictionary

def print_table(array):
    # get col_width
    col_width = []
    for row in array:
        for i, cell in enumerate(row):
            if len(col_width) <= i:
                col_width.append(0)
            if len(cell) > col_width[i]:
                col_width[i] = len(cell)
    # get total width
    total_width = 0
    for width in col_width:
        total_width += width
    # print output
    for row_index,row in enumerate(array):
        output_row = []
        for i,cell in enumerate(row):
            width = col_width[i]
            output_row.append(cell.ljust(width, ' '))
        output_row = ' | '.join(output_row)
        print(output_row)
        separator = '-' if row_index>0 else '='
        print(''.ljust(total_width+(3*(len(row)-1)) , separator))

def get_reminded_tasks():
    kanban = load_kanban()
    tasks = kanban["tasks"]
    current_time = time.time()
    reminded_tasks = {}
    for task_id in tasks.keys():
        task = tasks[task_id]
        if complete_str_timestamp(task["remind_on"].strip()) != "":
            time_start = str_to_timestamp(task["remind_on"])
            time_stop = time_start + float(task["remind_for"])
            if time_start < current_time and time_stop > current_time:
                reminded_tasks[task_id] = task
    return reminded_tasks

def add_task(arg_dict={}):
    kanban = load_kanban()
    if 'name' in arg_dict.keys():
        id = arg_dict['id'] if 'id' in arg_dict.keys() else generate_dictionary_id(kanban['tasks'])
        id = str(id)
        task = DEFAULT_TASK
        if id not in kanban['tasks'].keys():
            # modify task
            for task_key in ('name', 'remind_on', 'remind_for'):
                if task_key in arg_dict.keys():
                    task[task_key] = arg_dict[task_key]
            # modify task's board
            if 'board' in arg_dict.keys():
                task['board'] = get_board_id(arg_dict['board'])
            kanban['tasks'][id] = task
            save_kanban(kanban)
        else:
            print('Task with id %s already exists' %(id,))
    else:
        print('You should specify task name')

def edit_task(arg_dict={}):
    kanban = load_kanban()
    if 'id' in arg_dict.keys():
        id = str(arg_dict['id'])
        if id in kanban['tasks'].keys():
            # get old task
            task = kanban['tasks'][id]
            # modify task
            for task_key in ('name', 'remind_on', 'remind_for'):
                if task_key in arg_dict.keys():
                    task[task_key] = arg_dict[task_key]
            # modify task's board
            if 'board' in arg_dict.keys():
                task['board'] = get_board_id(arg_dict['board'])
            kanban['tasks'][id] = task
            save_kanban(kanban)
        else:
            print('Task with id %s doesn\'t exists' %(id,))
    else:
        print('You should specify task id')

def delete_task(arg_dict={}):
    kanban = load_kanban()
    if 'id' in arg_dict.keys():
        id = str(arg_dict['id'])
        if id in kanban['tasks'].keys():
            kanban['tasks'].pop(id, None) # delete from kanban['tasks']
            save_kanban(kanban)
        else:
            print('Task with id %s doesn\'t exists' %(id,))
    else:
        print('You should specify task id')

def show_task(arg_dict={}):
    kanban = load_kanban()
    boards = kanban['boards']
    tasks = kanban['tasks']
    for id in sorted(tasks, key = lambda key: int(key)):
        task = tasks[id]
        task_name = task['name']
        task_board = boards[task['board']] if task['board'] in boards.keys() else ''
        remind_on = task['remind_on']
        remind_for = task['remind_for']
        print('%s. \t %s \t %s \t %s \t %s' %(id, task_name, task_board, remind_on, remind_for))

def add_board(arg_dict={}):
    kanban = load_kanban()
    if 'name' in arg_dict.keys():
        id = arg_dict['id'] if 'id' in arg_dict.keys() else generate_dictionary_id(kanban['boards'])
        id = str(id)
        name = arg_dict['name']
        if id not in kanban['boards'].keys():
            kanban['boards'][id] = name
            save_kanban(kanban)
        else:
            print('Board with id %s already exists' %(id,))
    else:
        print('You should specify board name')

def edit_board(arg_dict={}):
    kanban = load_kanban()
    if 'id' in arg_dict.keys() and 'name' in arg_dict.keys():
        id = str(arg_dict['id'])
        name = arg_dict['name']
        if id in kanban['boards'].keys():
            kanban['boards'][id] = name
            save_kanban(kanban)
        else:
            print('Board with id %s doesn\'t exists' %(id,))
    else:
        print('You should specify board id and name')

def delete_board(arg_dict={}):
    kanban = load_kanban()
    if 'id' in arg_dict.keys():
        id = str(arg_dict['id'])
        if id in kanban['boards'].keys():
            kanban['boards'].pop(id, None) # delete from kanban['boards']
            save_kanban(kanban)
        else:
            print('Board with id %s doesn\'t exists' %(id,))
    else:
        print('You should specify board id')

def show_board(arg_dict={}):
    kanban = load_kanban()
    boards = kanban['boards']
    for id in sorted(boards, key = lambda key: int(key)):
        print('%s. \t %s' %(id, boards[id]))

def edit_config(arg_dict={}):
    configuration = load_configuration()
    for key in arg_dict.keys():
        if key in configuration:
            configuration[key] = arg_dict[key]
    save_configuration(configuration)

def show_config(arg_dict={}):
    configuration = load_configuration()
    for key in configuration.keys():
        print('%s\t:%s' %(key.ljust(20,' '), configuration[key]))

def kanban(arg_dict={}):
    kanban = load_kanban()
    boards = kanban['boards']
    tasks = kanban['tasks']
    # get all board_id that have at least one task
    task_boards = [tasks[task_id]['board'] for task_id in tasks if tasks[task_id]['board'] in boards]
    # let boards on contains board having tasks
    boards = {x:boards[x] for x in boards if x in task_boards}
    # get board's tasks and max_task_count
    max_task_count = 0
    for board_id in boards:
        board_name = boards[board_id]
        boards[board_id] = {
                'name' : board_name,
                'tasks' : []
            }
        for task_id in tasks.keys():
            task = tasks[task_id]
            if task['board'] == board_id:
                task['id'] = task_id
                boards[board_id]['tasks'].append(task)
        task_count = len(boards[board_id]['tasks'])
        if task_count > max_task_count:
            max_task_count = task_count
    # assemble outputs
    outputs = [[]]
    # captions
    for key in boards.keys():
        outputs[0].append(boards[key]['name'])
    for i in range(max_task_count):
        output = []
        for board_id in boards:
            task = boards[board_id]['tasks'][i]
            output.append('%s. %s %s' %(task['id'], task['name'], task['remind_on']))
        outputs.append(output)
    # print outputs
    print_table(outputs)

def pomodoro(arg_dict={}):
    config = load_configuration()
    kanban = load_kanban()
    old_reminded_task_list = []
    paused = False
    play_alarm = False
    alarm_ring = False
    play_tick = config['play_tick']
    state = 'work'
    counter = config['work_time']
    small_counter = 0
    # get fd etc
    fd = sys.stdin.fileno()
    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)
    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)
    try:
        print '(q) Quit        (t) Toggle Mode     (space) Pause/Resume'
        print '   (k) Toggle tick    (r) Reload    (s) Turn Off Alarm'
        while True:
            try:
                # small counter is used to make the system more responsive
                time.sleep(0.1)
                small_counter += 1
                if small_counter == 10:
                    small_counter = 0
                    if not paused:
                        counter -= 1
                        if counter == 0:
                            switch_beep()
                            # Switch state
                            state = 'work' if state == 'rest' else 'rest'
                            counter = config[state + '_time']
                    if play_alarm and alarm_ring:
                        alarm_beep()
                    elif play_tick and state == 'work':
                        tick_beep()
                # show tasks
                new_reminded_task_list = get_reminded_tasks()
                if new_reminded_task_list != old_reminded_task_list:
                    old_reminded_task_list = new_reminded_task_list
                    alarm_ring = True
                # show pomodoro
                output = '\r' + state.capitalize() + ' ' + get_formatted_counter(counter)
                sys.stdout.write(output.ljust(30, ' '))
                sys.stdout.flush()
                # read user input
                try:
                    user_input = sys.stdin.read(1)
                    if user_input == ' ': # Pause/resume
                        paused = not paused
                    elif user_input == 'q': # Close
                        break
                    elif user_input == 't': # Switch state
                        state = 'work' if state == 'rest' else 'rest'
                        counter = config[state + '_time']
                    elif user_input == 'r': # Reload kanban
                        kanban = load_kanban()
                    elif user_input == 's': # Turn off alarm
                        play_alarm = False
                    elif user_input == 'k':
                        play_tick = not play_tick
                except IOError:
                    pass
            except(KeyboardInterrupt):
                break
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
    print('')

def help(arg_dict={}):
    print('')
    print(' KANBAN & POMODORO')
    print('  * time-wizard.py kanban')
    print('  * time-wizard.py pomodoro')
    print('')
    print(' CONFIGURATION')
    print('  * time-wizard.py show-config')
    print('  * time-wizard.py edit-config key:value')
    print('')
    print(' BOARDS')
    print('  * time-wizard.py show-board')
    print('  * time-wizard.py add-board name:board-name')
    print('  * time-wizard.py edit-board id:board-id, key:board-name')
    print('  * time-wizard.py delete-board id:board-id')
    print('')
    print(' TASKS')
    print('  * time-wizard.py show-task')
    print('  * time-wizard.py add-task key:value, key:value,...')
    print('  * time-wizard.py edit-task id:task-id, key:value,...')
    print('  * time-wizard.py delete-task id:task-id')
    print(' Available Keys: name, board, remind_on, remind_for ')

def test(arg_dict={}):
    pass

if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else '' # get command
    command_list = {
            'add-task' : add_task,
            'edit-task' : edit_task,
            'delete-task' : delete_task,
            'show-task' : show_task,
            'add-board' : add_board,
            'edit-board' : edit_board,
            'delete-board' : delete_board,
            'show-board' : show_board,
            'edit-config' : edit_config,
            'show-config' : show_config,
            'kanban' : kanban,
            'pomodoro' : pomodoro,
            'help' : help,
            'test' : test
        }
    if command in command_list:
        arg_string = ' '.join(sys.argv[2:]) # get arguments
        arg_dict = str_as_dictionary(arg_string) # turn arguments into dictionary
        command_list[command](arg_dict) # run the command
    else:
        help()
