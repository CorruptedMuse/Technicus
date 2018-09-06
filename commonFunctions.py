from openpyxl import load_workbook
import time


def merge_strings(string_array):
    result = ""
    for segment in string_array:
        result = "{0}{1} ".format(result, segment)
    return result[:-1]


def log(event, user, channel, state1, state2):
    # Log format: time, event, user, channel, first state, second state
    print("Recording a {}".format(event))
    wb = load_workbook("logs.xlsx")
    sheet_name = time.strftime("%b%y", time.gmtime())
    ws = None
    for sheet in wb:
        if sheet.title == sheet_name:
            ws = sheet
    if not ws:
        ws = wb.create_sheet(sheet_name)

    row = 1
    while ws['A{}'.format(row)].value is not None:
        row = row + 1
    ws['A{}'.format(row)] = time.asctime(time.gmtime())
    ws['B{}'.format(row)] = event
    if user is not None:
        ws['C{}'.format(row)] = user.name
        ws['D{}'.format(row)] = user.id
    if channel is not None:
        ws['E{}'.format(row)] = channel.name
        ws['F{}'.format(row)] = channel.id
    ws['G{}'.format(row)] = str(state1)
    ws['H{}'.format(row)] = str(state2)
    wb.save("logs.xlsx")