'''
Created on 2014-3-24

@author: fengjian
'''
import matplotlib.pyplot as plt


def do_clients_plot():
    plt.title(u"Clients Status")
    plt.xlabel(u"Time")
    plt.ylabel(u"Number")
    x=[1,2,3,4,5]
    y1=[12,3,4,5,6]
    y2=[2,3,45,6,7]
    plt.plot(x,y1)
    plt.plot(x,y2)
    plt.show()

if __name__ == '__main__':
    
    do_clients_plot()
    pass