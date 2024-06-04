from django.shortcuts import render
from django.contrib.auth import get_user_model

def staff_users_list(request):
    User = get_user_model()
    staff_users = User.objects.filter(is_staff=True)
    context = {'staff_users': staff_users}
    return render(request, 'studentapp/teacher_list.html', context)

