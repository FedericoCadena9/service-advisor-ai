import type {
  AppointmentResponse,
  SmsDeliveryResponse,
  SmsPreviewResponse,
} from './generated/types.gen'
import {
  advanceMessageMessagesDeliveryIdAdvancePost,
  enqueueSmsQuotesQuoteIdMessagesPost,
  previewSmsQuotesQuoteIdSmsPreviewPost,
  reserveAppointmentQuotesQuoteIdAppointmentPost,
} from './generated/sdk.gen'
import { requestFailed } from './failure'

export async function reserveAppointment(token: string, quoteId: string): Promise<AppointmentResponse> {
  const response = await reserveAppointmentQuotesQuoteIdAppointmentPost({
    headers: { authorization: `Bearer ${token}` },
    path: { quote_id: quoteId },
  })
  if (!('data' in response) || !response.data) throw requestFailed('Appointment unavailable', response)
  return response.data
}

export async function previewSms(token: string, quoteId: string): Promise<SmsPreviewResponse> {
  const response = await previewSmsQuotesQuoteIdSmsPreviewPost({
    headers: { authorization: `Bearer ${token}` },
    path: { quote_id: quoteId },
  })
  if (!('data' in response) || !response.data) throw requestFailed('Message preview unavailable', response)
  return response.data
}

export async function sendSms(token: string, quoteId: string, text: string): Promise<SmsDeliveryResponse> {
  const response = await enqueueSmsQuotesQuoteIdMessagesPost({
    body: { text },
    headers: { authorization: `Bearer ${token}` },
    path: { quote_id: quoteId },
  })
  if (!('data' in response) || !response.data) throw requestFailed('Message was not enqueued', response)
  return response.data
}

export async function advanceMessage(token: string, deliveryId: string): Promise<SmsDeliveryResponse> {
  const response = await advanceMessageMessagesDeliveryIdAdvancePost({
    headers: { authorization: `Bearer ${token}` },
    path: { delivery_id: deliveryId },
  })
  if (!('data' in response) || !response.data) throw requestFailed('Message timeline unavailable', response)
  return response.data
}
