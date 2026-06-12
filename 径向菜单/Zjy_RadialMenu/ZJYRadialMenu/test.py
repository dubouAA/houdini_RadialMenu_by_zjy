import os ,json
# from PySide2.QtGui import QPixmap,QCursor,QPainter, QColor, QPen, QBrush, QFont, QRegion, QPainterPath,QRadialGradient,QConicalGradient

# t = {'1':1,'2':2,'3':3}
# y = {(1,2):1,(2,3):2,(3,4):3}
# print(y[(1,2)])
# sort = sorted(y,key=lambda x:x[1])
# for i,j in sort.item():
#     print(i)
color_json_path = os.path.join(os.path.dirname(__file__), 'radiaMene_color.json')
json_color_data = json.load(open(color_json_path))
# center_color = QColor(json_color_data['center_color'])

print(type(json_color_data['center_color']))
'''
{"r":250,"g":250,"b":100,"a":220}
{"r":100,"g":250,"b":250,"a":220}
{"r":250,"g":100,"b":250,"a":220}
{"r":250,"g":130,"b":130,"a":220}
{"r":250,"g":185,"b":105,"a":220}
{"r":250,"g":240,"b":90,"a":220}
{"r":35,"g":255,"b":70,"a":220}
{"r":35,"g":127,"b":255,"a":220}
{"r":167,"g":35,"b":255,"a":220}
{"r":35,"g":50,"b":255,"a":220}

'''
file_path =  os.path.dirname(os.path.realpath(__file__)).replace('\\','/')
print(file_path)