from django.shortcuts import render
from django.db.models import *
from django.db import transaction
from sistema_buap_api.serializers import *
from sistema_buap_api.models import *
from rest_framework.authentication import BasicAuthentication, SessionAuthentication, TokenAuthentication
from rest_framework.generics import CreateAPIView, DestroyAPIView, UpdateAPIView
from rest_framework import permissions
from rest_framework import generics
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from django.core import serializers
from django.utils.html import strip_tags
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters
from datetime import datetime
from django.conf import settings
from django.template.loader import render_to_string
import string
import random
import json

class MaestrosAll(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    def get(self, request, *args, **kwargs):
        maestros = Maestros.objects.filter(user__is_active = 1).order_by("id")
        maestros = MaestroSerializer(maestros, many=True).data
        #Aquí convertimos los valores de nuevo a un array
        if not maestros:
            return Response({},400)
        for maestro in maestros:
            maestro["materias_json"] = json.loads(maestro["materias_json"])

        return Response(maestros, 200)
    
class MaestrosView(generics.CreateAPIView):
    #Obtener usuario por ID
    def get(self, request, *args, **kwargs):
        try:
            maestro = get_object_or_404(Maestros, id=request.GET.get("id"))
            maestro = MaestroSerializer(maestro, many=False).data
            maestro["materias_json"] = json.loads(maestro["materias_json"])
            return Response(maestro, 200)
        except Exception as e:
            return Response({"error": str(e)}, 404)
    
    #Registrar nuevo usuario
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = UserSerializer(data=request.data)
        if user.is_valid():
            #Grab user data
            role = request.data['rol']
            first_name = request.data['first_name']
            last_name = request.data['last_name']
            email = request.data['email']
            password = request.data['password']
            #Valida si existe el usuario o bien el email registrado
            existing_user = User.objects.filter(email=email).first()

            if existing_user:
                return Response({"message":"Username "+email+", is already taken"},400)

            user = User.objects.create( username = email,
                                        email = email,
                                        first_name = first_name,
                                        last_name = last_name,
                                        is_active = 1)

            user.save()
            user.set_password(password)
            user.save()

            group, created = Group.objects.get_or_create(name=role)
            group.user_set.add(user)
            user.save()

            #Create a profile for the user
            maestro = Maestros.objects.create(user=user,
                                            id_trabajador= request.data["id_trabajador"],
                                            fecha_nacimiento= request.data["fecha_nacimiento"],
                                            telefono= request.data["telefono"],
                                            rfc= request.data["rfc"].upper(),
                                            cubiculo= request.data["cubiculo"],
                                            area_investigacion= request.data["area_investigacion"],
                                            materias_json = json.dumps(request.data["materias_json"]))
            maestro.save()

            return Response({"maestro_created_id": maestro.id }, 201)

        return Response(user.errors, status=status.HTTP_400_BAD_REQUEST)

class MaestrosViewEdit(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    #Actualizar maestro
    def put(self, request, *args, **kwargs):
        maestro = get_object_or_404(Maestros, id=request.data.get("id"))
        user = maestro.user
        
        #Actualizar datos del usuario
        user.first_name = request.data.get("first_name", user.first_name)
        user.last_name = request.data.get("last_name", user.last_name)
        user.email = request.data.get("email", user.email)
        user.save()
        
        #Actualizar datos del maestro
        maestro.id_trabajador = request.data.get("id_trabajador", maestro.id_trabajador)
        maestro.fecha_nacimiento = request.data.get("fecha_nacimiento", maestro.fecha_nacimiento)
        maestro.telefono = request.data.get("telefono", maestro.telefono)
        maestro.rfc = request.data.get("rfc", maestro.rfc).upper()
        maestro.cubiculo = request.data.get("cubiculo", maestro.cubiculo)
        maestro.area_investigacion = request.data.get("area_investigacion", maestro.area_investigacion)
        maestro.materias_json = json.dumps(request.data.get("materias_json", json.loads(maestro.materias_json)))
        maestro.save()
        
        return Response({"message": "Maestro actualizado correctamente"}, 200)
    
    #Eliminar maestro
    def delete(self, request, *args, **kwargs):
        maestro = get_object_or_404(Maestros, id=request.GET.get("id"))
        user = maestro.user
        
        #Desactivar usuario
        user.is_active = 0
        user.save()
        
        return Response({"message": "Maestro eliminado correctamente"}, 200)