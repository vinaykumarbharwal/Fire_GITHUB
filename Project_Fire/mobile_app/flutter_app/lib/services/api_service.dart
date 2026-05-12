import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:location/location.dart';

import '../utils/constants.dart';

class ApiService extends ChangeNotifier {
  static const String baseUrl = AppConstants.baseUrl;
  
  Future<Map<String, dynamic>> reportDetection({
    required Map<String, dynamic> detection,
    required XFile imageFile,
  }) async {
    try {
      // Get location
      Location location = Location();
      bool serviceEnabled = await location.serviceEnabled();
      if (!serviceEnabled) {
        serviceEnabled = await location.requestService();
        if (!serviceEnabled) {
          throw Exception('Location services are disabled');
        }
      }

      PermissionStatus permissionGranted = await location.hasPermission();
      if (permissionGranted == PermissionStatus.denied) {
        permissionGranted = await location.requestPermission();
        if (permissionGranted != PermissionStatus.granted) {
          throw Exception('Location permissions are denied');
        }
      }

      var currentLocation = await location.getLocation();

      // Create multipart request (Web-compatible using bytes)
      var uri = Uri.parse('$baseUrl/detections/report');
      var request = http.MultipartRequest('POST', uri);

      // Read image as bytes (works on Web + Native)
      final Uint8List imageBytes = await imageFile.readAsBytes();
      final filename = 'detection_${DateTime.now().millisecondsSinceEpoch}.jpg';
      request.files.add(
        http.MultipartFile.fromBytes(
          'image',
          imageBytes,
          filename: filename,
        ),
      );

      // Add fields
      request.fields['latitude'] = currentLocation.latitude.toString();
      request.fields['longitude'] = currentLocation.longitude.toString();
      request.fields['confidence'] = detection['confidence'].toString();
      request.fields['timestamp'] = detection['timestamp'];

      // Send request
      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200 || response.statusCode == 201) {
        var data = json.decode(response.body);
        print('✅ Detection reported: ${data["detection_id"]}');
        return data;
      } else {
        throw Exception('Server error: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      print('❌ Error reporting detection: $e');
      throw Exception('Failed to report detection: $e');
    }
  }

  Future<List<dynamic>> getDetections({int limit = 50}) async {
    try {
      var uri = Uri.parse('$baseUrl/detections?limit=$limit');
      var response = await http.get(uri);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to load detections');
      }
    } catch (e) {
      print('Error loading detections: $e');
      return [];
    }
  }

  Future<Map<String, dynamic>> getStats() async {
    try {
      var uri = Uri.parse('$baseUrl/stats');
      var response = await http.get(uri);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Failed to load stats');
      }
    } catch (e) {
      print('Error loading stats: $e');
      return {};
    }
  }



  Future<Map<String, dynamic>> detectFireCloud(XFile imageFile, {double lat = 0.0, double lng = 0.0}) async {
    try {
      var uri = Uri.parse('$baseUrl/inference/detect');
      var request = http.MultipartRequest('POST', uri);

      // Add Coordinates
      request.fields['lat'] = lat.toString();
      request.fields['lng'] = lng.toString();

      // Web-compatible: use bytes instead of fromPath
      final Uint8List imageBytes = await imageFile.readAsBytes();
      request.files.add(
        http.MultipartFile.fromBytes(
          'image',
          imageBytes,
          filename: imageFile.name,
        ),
      );

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        throw Exception('Inference failed: ${response.statusCode}');
      }
    } catch (e) {
      print('Cloud inference error: $e');
      return {'status': 'error', 'message': e.toString()};
    }
  }
}