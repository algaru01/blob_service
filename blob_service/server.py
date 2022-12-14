#!/usr/bin/env python3

from flask import make_response, request, send_from_directory

from blob_service.database import WrongBlobId, BlobIdInUse, WrongUserId
from blob_service.authService import AuthService, UserNotFound

import os.path

def routeApp(app, DATABASE, authServer_url, blob_storage):

    auth_server = AuthService(authServer_url)

    @app.route('/v1/blob/<blob_id>', methods=['PUT'])
    def create_blob(blob_id):
        if "user-token" in request.headers:
            token = request.headers["user-token"]
        if "admin-token" in request.headers:
            token = request.headers["admin-token"]
        if token is None:
            return make_response("Not 'user-token' or 'admin-token' found in header.", 401)
        try:
            user_token = auth_server.user_of_token(token)
        except UserNotFound:
            return make_response(f"User token not valid", 401)

        if "user" not in request.form:
            return make_response("Missing 'user' param", 400)
        if "file" not in request.files:
            return make_response("Missing 'file' param", 400)

        if request.form["user"] != user_token:
            return make_response(f"User token different to user", 401)

        user = request.form["user"]
        blob_location = f'{blob_storage}/blob_{blob_id}'

        try:
            DATABASE.create_blob(blob_id, blob_location)
        except BlobIdInUse:
            return make_response("Blob ID already in use", 400)

        file = request.files['file']     
        file.save(blob_location)

        try:
            DATABASE.add_wPermission(blob_id, user)
            DATABASE.add_rPermission(blob_id, user)
        except WrongBlobId:
            return make_response("Blob not found", 404)
        except WrongUserId:
            return make_response("User not found", 404)

        return make_response(blob_id, 200)

    @app.route('/v1/blob/<blob_id>', methods=['DELETE'])
    def remove_blob(blob_id):
        if "user-token" in request.headers:
            token = request.headers["user-token"]
        if "admin-token" in request.headers:
            token = request.headers["admin-token"]
        if token is None:
            return make_response("Not 'user-token' or 'admin-token' found in header.", 401)
        try:
            user_token = auth_server.user_of_token(token)
        except UserNotFound:
            return make_response(f"User token not valid", 401)

        if not request.is_json:
            return make_response('Missing JSON', 400)
        if "user" not in request.get_json():
            return make_response("Missing 'user' param", 400)

        user = request.get_json()['user']

        if user != user_token:
            return make_response(f"User token different to user", 401)

        try:
            res = DATABASE.get_blob(blob_id)
            blob_location = res[1]
        except WrongBlobId:
            return make_response("Blob not found.", 404)
        
        if not DATABASE.has_wPermission(user_token, blob_id):
            return make_response(f"User doesn't have write permission over this blob", 401)

        try:
            DATABASE.delete_blob(blob_id)
        except WrongBlobId:
            return make_response(f"Blob not found", 404)
            
        try:
            os.remove(blob_location)
        except FileNotFoundError:
            return make_response(f"Blob {blob_id} deleted correctly from db but file was not found", 200)

        return make_response(f"Blob {blob_id} deleted correctly", 200)

    @app.route('/v1/blob/<blob_id>', methods=['POST'])
    def update_blob(blob_id):
        if "user-token" in request.headers:
            token = request.headers["user-token"]
        if "admin-token" in request.headers:
            token = request.headers["admin-token"]
        if token is None:
            return make_response("Not 'user-token' or 'admin-token' found in header.", 401)
        try:
            user_token = auth_server.user_of_token(token)
        except UserNotFound:
            return make_response(f"User token not valid", 401)


        if "file" not in request.files:
            return make_response("Missing 'file' param", 400)
        if "user" not in request.form:
            return make_response("Missing 'user' param", 400)

        if request.form["user"] != user_token:
            return make_response(f"User token different to user", 401)

        try:
            res = DATABASE.get_blob(blob_id)
            blob_location = res[1]
        except WrongBlobId:
            return make_response("Blob not found.", 404)

        if not DATABASE.has_wPermission(user_token, blob_id):
            return make_response("User does not have writable permissions over this blob.", 401)

        file = request.files['file']     
        file.save(blob_location)

        return make_response("File updated correctly.", 200)

    @app.route('/v1/blob/<blob_id>', methods=['GET'])
    def get_blob(blob_id):
        if "user-token" in request.headers:
            token = request.headers["user-token"]
        if "admin-token" in request.headers:
            token = request.headers["admin-token"]
        if token is None:
            return make_response("Not 'user-token' or 'admin-token' found in header.", 401)
        try:
            user_id = auth_server.user_of_token(token)
        except UserNotFound:
            return make_response(f"User token not valid", 401)

        if "user" not in request.args:
            return make_response('Missing "user" param', 400)

        if request.args["user"] != user_id:
            return make_response(f"User token different to user", 401)

        try:
            DATABASE.get_blob(blob_id)
        except WrongBlobId:
            return make_response("Blob not found.", 404)

        try:
            if not DATABASE.has_rPermission(user_id, blob_id):
                return make_response(f"User has not readable permissions over this blob", 401)
        except WrongBlobId:
            return make_response("Blob not found", 404)

        try:
            res_db = DATABASE.get_blob(blob_id)
            local_file = res_db[1]
        except WrongBlobId:
            return make_response("Blob not found", 404)

        file_abspath = os.path.abspath(local_file)
        directory, filename = os.path.split(file_abspath)

        return send_from_directory(path=filename, directory=f'{directory}/')

    @app.route('/v1/blob/<blob_id>/writable_by/<user>', methods=['PUT'])
    def add_wPermission_blob(blob_id, user):
        if "user-token" in request.headers:
            token = request.headers["user-token"]
        if "admin-token" in request.headers:
            token = request.headers["admin-token"]
        if token is None:
            return make_response("Not 'user-token' or 'admin-token' found in header.", 401)
        try:
            user_token = auth_server.user_of_token(token)
        except UserNotFound:
            return make_response(f"User token not valid", 401)

        if not request.is_json:
            return make_response('Missing JSON', 400)

        try:
            DATABASE.get_blob(blob_id)
        except WrongBlobId:
            return make_response("Blob not found.", 404)

        if not DATABASE.has_wPermission(user_token, blob_id):
            return make_response(f"User doesn't have writable permission.", 404)

        if DATABASE.has_wPermission(user, blob_id):
            return make_response(f"{user} already has writable privilege.", 204)

        try:
            DATABASE.add_wPermission(blob_id, user)
        except WrongUserId:
            return make_response(f"User not found", 404)
        except WrongBlobId:
            return make_response(f"Blob not found", 404)

        return make_response(f"Added writable permission to {user} for {blob_id}", 200)

    @app.route('/v1/blob/<blob_id>/writable_by/<user>', methods=['DELETE'])
    def remove_wPermission_blob(blob_id, user):
        if "user-token" in request.headers:
            token = request.headers["user-token"]
        if "admin-token" in request.headers:
            token = request.headers["admin-token"]
        if token is None:
            return make_response("Not 'user-token' or 'admin-token' found in header.", 401)
        try:
            user_token = auth_server.user_of_token(token)
        except UserNotFound:
            return make_response(f"User token not valid", 401)

        if not request.is_json:
            return make_response('Missing JSON', 400)

        try:
            DATABASE.get_blob(blob_id)
        except WrongBlobId:
            return make_response("Blob not found.", 404)

        if not DATABASE.has_wPermission(user_token, blob_id):
            return make_response(f"User doesn't have writable permission.", 404)

        try:
            DATABASE.remove_wPermission(blob_id, user)
        except WrongUserId:
            return make_response(f"User not found", 404)
        except WrongBlobId:
            return make_response(f"Blob not found", 404)

        return make_response(f"Removed writable permission to {user} for {blob_id}", 204)

    @app.route('/v1/blob/<blob_id>/readable_by/<user>', methods=['PUT'])
    def add_rPermission_blob(blob_id, user):
        if "user-token" in request.headers:
            token = request.headers["user-token"]
        if "admin-token" in request.headers:
            token = request.headers["admin-token"]
        if token is None:
            return make_response("Not 'user-token' or 'admin-token' found in header.", 401)
        try:
            user_token = auth_server.user_of_token(token)
        except UserNotFound:
            return make_response(f"User token not valid", 401)

        if not request.is_json:
            return make_response('Missing JSON', 400)

        try:
            DATABASE.get_blob(blob_id)
        except WrongBlobId:
            return make_response("Blob not found.", 404)

        if not DATABASE.has_wPermission(user_token, blob_id):
            return make_response(f"User doesn't have writable permission.", 404)

        if DATABASE.has_rPermission(user, blob_id):
            return make_response(f"{user} already has readable privilege.", 204)

        try:
            DATABASE.add_rPermission(blob_id, user)
        except WrongUserId:
            return make_response(f"User not found", 404)
        except WrongBlobId:
            return make_response(f"Blob not found", 404)

        return make_response(f"Added readable permission to {user} for {blob_id}", 200)

    @app.route('/v1/blob/<blob_id>/readable_by/<user>', methods=['DELETE'])
    def remove_rPermission_blob(blob_id, user):
        if "user-token" in request.headers:
            token = request.headers["user-token"]
        if "admin-token" in request.headers:
            token = request.headers["admin-token"]
        if token is None:
            return make_response("Not 'user-token' or 'admin-token' found in header.", 401)
        try:
            user_token = auth_server.user_of_token(token)
        except UserNotFound:
            return make_response(f"User token not valid", 401)

        if not request.is_json:
            return make_response('Missing JSON', 400)

        try:
            DATABASE.get_blob(blob_id)
        except WrongBlobId:
            return make_response("Blob not found.", 404)

        if not DATABASE.has_wPermission(user_token, blob_id):
            return make_response(f"User doesn't have writable permission.", 404)

        try:
            DATABASE.remove_rPermission(blob_id, user)
        except WrongUserId:
            return make_response(f"User not found", 404)
        except WrongBlobId:
            return make_response(f"Blob not found", 404)

        return make_response(f"Removed readable permission to {user} for {blob_id}", 204)