from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return render(request, 'track/index.j2', {'context_var' : 'hey'})

def read(request):
    return HttpResponse("Read")