from speaker_identification.speaker_identification import identify_speaker,  identify_speaker_denoised
import os
from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from google.cloud import storage
from google.api_core import page_iterator
from reveal.models import Pooi, ScanResult
from reveal.serializers import PooiSerializer, ScanResultSerializer

class MatchVoices(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from django.core.files.storage import FileSystemStorage
        voice1 = self.request.FILES['voice1']
        voice2 = self.request.FILES['voice2']

        if voice2 and voice1:
            fs = FileSystemStorage()

            v1 = fs.save(voice1.name, voice1)
            v1_path = fs.path(v1)

            v2 = fs.save(voice2.name, voice2)
            v2_path = fs.path(v2)

            from speechbrain.pretrained import SpeakerRecognition
            verification = SpeakerRecognition.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb",
                                                           savedir="pretrained_models/spkrec-ecapa-voxceleb")
            score, prediction = verification.verify_files(v1_path, v2_path)
            # score, prediction = verification.verify_files(file1, file2)
            data = {
                # 'score': voice1.name,
                # 'prediction': voice2.name
                'score': score,
                'prediction': prediction
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            data = {
                'message': 'Hello Django REST API'
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

def list_directories(bucket_name, prefix, gcs):
    if prefix and not prefix.endswith('/'):
        prefix += '/'

    extra_params = {
        "projection": "noAcl",
        "prefix": prefix,
        "delimiter": '/'
    }

    # gcs = storage.Client()

    path = "/b/" + bucket_name + "/o"

    iterator = page_iterator.HTTPIterator(
        client=gcs,
        api_request=gcs._connection.api_request,
        path=path,
        items_key='prefixes',
        item_to_value=_item_to_value,
        extra_params=extra_params,
    )

    return [x for x in iterator]

class IdentifySpeaker(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        voice = self.request.FILES['voice']
        if voice:
            id_data = identify_speaker(voice)
            id_data_denoised = identify_speaker_denoised(id_data[5], id_data[4])
            id = id_data[0]
            accuracy = id_data[1]
            id2 = id_data[2]
            accuracy2 = id_data[3]
            from django.core.files.base import ContentFile, File
            denoised_voice = None

            did = id_data_denoised[0]
            daccuracy = id_data_denoised[1]
            did2 = id_data_denoised[2]
            daccuracy2 = id_data_denoised[3]

            if id:
                # id = int(id)+1 97073197 3600
                pooi = Pooi.objects.filter(id=id).first()
                pooi2 = Pooi.objects.filter(id=id2).first()

                pooi_data = PooiSerializer(pooi).data
                pooi2_data = PooiSerializer(pooi2).data

                dpooi = Pooi.objects.filter(id=did).first()
                dpooi2 = Pooi.objects.filter(id=did2).first()

                dpooi_data = PooiSerializer(dpooi).data
                dpooi2_data = PooiSerializer(dpooi2).data

                # scanResult = ScanResult(voice=voice, score=float(str(accuracy)), denoisedScore=float(str(accuracy2)), denoisedVoice=voice, pooi=pooi,  denoisedPooi=pooi2, created_by=request.user)
                # scanResult = ScanResult(voice=voice, score=0.0, denoisedScore=0.0, denoisedVoice=voice, pooi=pooi,  denoisedPooi=pooi2, created_by=request.user)

                with open(id_data[4], 'rb') as f:
                    denoised_voice = File(f, name=os.path.basename(f.name))

                    print('-------------------------------')
                    print(type(denoised_voice))

                    scanResult = ScanResult(voice=voice,  denoisedVoice=denoised_voice, pooi=pooi,  denoisedPooi=pooi2, created_by=request.user)
                    dscanResult = ScanResult(voice=voice,  denoisedVoice=denoised_voice, pooi=dpooi,  denoisedPooi=dpooi2, created_by=request.user)
                    print('-----------brand logo type 0')
                    if request.user is not None and request.user.is_authenticated:
                        print('-----------brand logo type 1')
                        scanResult.created_by = request.user
                        print('-----------brand logo type  2')
                    print('-----------brand logo type 3')
                    scanResult.save()
                    print('-----------brand logo type4')
                # score
                data = {
                    'success': True,
                    "score": accuracy,
                    "id": id,
                    "pooi": pooi_data,
                    "denoised_score": accuracy2,
                    "denoised_pooi": pooi2_data,
                    "scanResult": ScanResultSerializer(scanResult).data,

                    "dscore": daccuracy,
                    "did": did,
                    "dpooi": dpooi_data,
                    "ddenoised_score": daccuracy2,
                    "ddenoised_pooi": dpooi2_data,

                }
                return Response(data, status=status.HTTP_200_OK)
            else:
                data = {
                    'message': 'POOI not found'
                }
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
        else:
            data = {
                'message': 'Voice file is required'
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)



class UpdateModel(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        storage_client = storage.Client.from_service_account_json('minfo-6b04e-ed4a5427f384.json')
        buckets = list(storage_client.list_buckets())
        print(buckets)
        bc_name = "minfo-6b04e.appspot.com"
        bucket = storage_client.get_bucket(bc_name)

        blobs2 = bucket.list_blobs(prefix="models/")
        print('-----------------------blobs:')
        print(blobs2)
        for blob in blobs2:
            print(blob.name)
            # destination_uri = '{}/{}'.format("/best_model", blob.name)
            blob.download_to_filename("speaker_identification/"+blob.name)

        blobs3 = bucket.list_blobs(prefix="denoised_models/")
        print('-----------------------blobs3:')
        print(blobs3)
        for blob in blobs3:
            print(blob.name)
            # destination_uri = '{}/{}'.format("/best_model", blob.name)
            blob.download_to_filename("speaker_identification/"+blob.name)



        data = {
            "success": True,
            'message': "Best trained model successfully updated",
        }
        return Response(data, status=status.HTTP_200_OK)


