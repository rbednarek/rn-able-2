from django.shortcuts import render

# Create your views here.
def single_upload(request):
    return render(request, 'data_upload/single_upload.html')
