/**
 * Google Ads Script: clone an Illinois Search campaign into Ohio and Indiana.
 *
 * Paste this into Google Ads > Tools > Bulk actions > Scripts.
 * Use Preview first. Preview mode is the dry run; Run creates paused campaigns.
 *
 * This uses AdsApp.search() to read the source campaign and AdsApp.mutateAll()
 * to create the new budgets, campaigns, state location target, ad groups,
 * keywords, and responsive search ads.
 */

const CONFIG = {
  sourceCampaignNameContains: 'schedule meeting',
  sourceCampaignId: 23586656126,
  targets: [
    { state: 'Ohio', abbreviation: 'OH', landingPage: 'https://billwithbomi.com/ohio' },
    { state: 'Indiana', abbreviation: 'IN', landingPage: 'https://billwithbomi.com/indiana' },
  ],
};

const KEYWORD_POLICY_EXEMPTIONS = {
  'SimplePractice billing help': [
    {
      policyName: 'THIRD_PARTY_CONSUMER_TECHNICAL_SUPPORT',
      violatingText: 'SimplePractice billing help',
    },
  ],
  'TherapyNotes billing service': [
    {
      policyName: 'THIRD_PARTY_CONSUMER_TECHNICAL_SUPPORT',
      violatingText: 'TherapyNotes billing service',
    },
  ],
  'Therapy Notes billing help': [
    {
      policyName: 'THIRD_PARTY_CONSUMER_TECHNICAL_SUPPORT',
      violatingText: 'Therapy Notes billing help',
    },
  ],
};

const EXCLUDED_SOURCE_KEYWORD_PATTERNS = [
  /\bharmonic office solutions\b/i,
];

const STATE_KEYWORD_REPLACEMENTS = {
  'illinois medicaid': {
    Ohio: [
      'ohio medicaid therapist billing',
      'ohio medicaid credentialing',
      'ohio medicaid provider enrollment',
    ],
    Indiana: [
      'indiana medicaid therapist billing',
      'indiana medicaid credentialing',
      'indiana medicaid provider enrollment',
    ],
  },
};

const STATE_CLONE_NEGATIVE_KEYWORDS = [
  'pregnant',
  'apply',
  'office',
  'phone number',
  'eligibility',
  'portal',
  'gov',
];

function main() {
  const customerId = AdsApp.currentAccount().getCustomerId().replace(/-/g, '');
  const sourceCampaign = getSourceCampaign_();
  const sourceBudget = getBudget_(sourceCampaign.campaignBudget);
  const adGroups = getAdGroups_(sourceCampaign.id);
  const keywords = getKeywords_(sourceCampaign.id);
  const ads = getResponsiveSearchAds_(sourceCampaign.id);
  const geoTargets = getGeoTargets_(CONFIG.targets.map((target) => target.state));

  Logger.log(`Source campaign: ${sourceCampaign.id} ${sourceCampaign.name}`);
  Logger.log(`Budget micros: ${sourceBudget.amountMicros}`);
  Logger.log(`Ad groups: ${adGroups.length}`);
  Logger.log(`Keywords: ${keywords.length}`);
  Logger.log(`Responsive search ads: ${ads.length}`);

  CONFIG.targets.forEach((target) => {
    const operations = buildOperationsForTarget_({
      customerId,
      sourceCampaign,
      sourceBudget,
      adGroups,
      keywords,
      ads,
      geoTargetResourceName: geoTargets[target.state],
      target,
    });

    Logger.log(`Creating paused ${target.state} clone with ${operations.length} operations.`);
    Logger.log(`Landing page: ${target.landingPage}`);
    const results = AdsApp.mutateAll(operations, { apiVersion: 'v24' });
    results.forEach((result, index) => {
      if (!result.isSuccessful()) {
        throw new Error(`Operation ${index} failed: ${result.getErrorMessages().join('; ')}`);
      }
      Logger.log(`Operation ${index}: ${result.getResourceName()}`);
    });
  });
}

function getSourceCampaign_() {
  const where = CONFIG.sourceCampaignId
    ? `campaign.id = ${Number(CONFIG.sourceCampaignId)}`
    : `campaign.name LIKE '%${escapeGaql_(CONFIG.sourceCampaignNameContains)}%'`;

  const rows = toRows_(`
    SELECT
      campaign.id,
      campaign.name,
      campaign.resource_name,
      campaign.advertising_channel_type,
      campaign.campaign_budget,
      campaign.bidding_strategy,
      campaign.bidding_strategy_type,
      campaign.manual_cpc.enhanced_cpc_enabled,
      campaign.maximize_conversions.target_cpa_micros,
      campaign.maximize_conversion_value.target_roas,
      campaign.target_spend.cpc_bid_ceiling_micros,
      campaign.network_settings.target_google_search,
      campaign.network_settings.target_search_network,
      campaign.network_settings.target_content_network,
      campaign.network_settings.target_partner_search_network,
      campaign.geo_target_type_setting.positive_geo_target_type,
      campaign.geo_target_type_setting.negative_geo_target_type,
      campaign.tracking_url_template,
      campaign.final_url_suffix
    FROM campaign
    WHERE ${where}
      AND campaign.status != 'REMOVED'
    ORDER BY campaign.id
  `);

  if (rows.length === 0) {
    throw new Error('No source campaign matched.');
  }
  if (rows.length > 1) {
    throw new Error(
      `Matched ${rows.length} campaigns. Set CONFIG.sourceCampaignId. ` +
        rows.map((row) => `${row.campaign.id}: ${row.campaign.name}`).join(', ')
    );
  }
  if (rows[0].campaign.advertisingChannelType !== 'SEARCH') {
    throw new Error(`Expected a SEARCH campaign, got ${rows[0].campaign.advertisingChannelType}.`);
  }
  return rows[0].campaign;
}

function getBudget_(budgetResourceName) {
  const rows = toRows_(`
    SELECT
      campaign_budget.id,
      campaign_budget.name,
      campaign_budget.amount_micros,
      campaign_budget.delivery_method
    FROM campaign_budget
    WHERE campaign_budget.resource_name = '${escapeGaql_(budgetResourceName)}'
  `);
  if (rows.length !== 1) {
    throw new Error(`Could not read source budget ${budgetResourceName}.`);
  }
  return rows[0].campaignBudget;
}

function getAdGroups_(campaignId) {
  return toRows_(`
    SELECT
      ad_group.id,
      ad_group.name,
      ad_group.status,
      ad_group.type,
      ad_group.cpc_bid_micros
    FROM ad_group
    WHERE campaign.id = ${Number(campaignId)}
      AND ad_group.status != 'REMOVED'
    ORDER BY ad_group.id
  `).map((row) => row.adGroup);
}

function getKeywords_(campaignId) {
  return toRows_(`
    SELECT
      ad_group.id,
      ad_group_criterion.status,
      ad_group_criterion.negative,
      ad_group_criterion.keyword.text,
      ad_group_criterion.keyword.match_type,
      ad_group_criterion.cpc_bid_micros
    FROM ad_group_criterion
    WHERE campaign.id = ${Number(campaignId)}
      AND ad_group_criterion.status != 'REMOVED'
      AND ad_group_criterion.type = 'KEYWORD'
    ORDER BY ad_group.id, ad_group_criterion.criterion_id
  `);
}

function getResponsiveSearchAds_(campaignId) {
  return toRows_(`
    SELECT
      ad_group.id,
      ad_group_ad.status,
      ad_group_ad.ad.final_urls,
      ad_group_ad.ad.responsive_search_ad.path1,
      ad_group_ad.ad.responsive_search_ad.path2,
      ad_group_ad.ad.responsive_search_ad.headlines,
      ad_group_ad.ad.responsive_search_ad.descriptions
    FROM ad_group_ad
    WHERE campaign.id = ${Number(campaignId)}
      AND ad_group_ad.status != 'REMOVED'
      AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'
    ORDER BY ad_group.id, ad_group_ad.ad.id
  `);
}

function getGeoTargets_(states) {
  const names = states.map((state) => `'${escapeGaql_(state)}'`).join(', ');
  const rows = toRows_(`
    SELECT
      geo_target_constant.name,
      geo_target_constant.resource_name
    FROM geo_target_constant
    WHERE geo_target_constant.country_code = 'US'
      AND geo_target_constant.target_type = 'State'
      AND geo_target_constant.name IN (${names})
      AND geo_target_constant.status = 'ENABLED'
  `);
  const found = {};
  rows.forEach((row) => {
    found[row.geoTargetConstant.name] = row.geoTargetConstant.resourceName;
  });
  states.forEach((state) => {
    if (!found[state]) {
      throw new Error(`Could not resolve geo target for ${state}.`);
    }
  });
  return found;
}

function buildOperationsForTarget_(context) {
  const {
    customerId,
    sourceCampaign,
    sourceBudget,
    adGroups,
    keywords,
    ads,
    geoTargetResourceName,
    target,
  } = context;

  const suffix = Date.now();
  const budgetTempId = '-1';
  const campaignTempId = '-2';
  const adGroupTempIds = {};
  adGroups.forEach((adGroup, index) => {
    adGroupTempIds[adGroup.id] = String(-1000 - index);
  });

  let campaignName = replaceStateText_(sourceCampaign.name, target);
  if (campaignName === sourceCampaign.name) {
    campaignName = `${sourceCampaign.name} - ${target.state}`;
  }
  campaignName = `${campaignName} ${suffix}`;

  const operations = [
    {
      campaignBudgetOperation: {
        create: {
          resourceName: `customers/${customerId}/campaignBudgets/${budgetTempId}`,
          name: `${campaignName} Budget`,
          amountMicros: sourceBudget.amountMicros,
          deliveryMethod: sourceBudget.deliveryMethod || 'STANDARD',
          explicitlyShared: false,
        },
      },
    },
    {
      campaignOperation: {
        create: buildCampaignCreate_(customerId, campaignTempId, budgetTempId, campaignName, sourceCampaign),
      },
    },
    {
      campaignCriterionOperation: {
        create: {
          campaign: `customers/${customerId}/campaigns/${campaignTempId}`,
          location: { geoTargetConstant: geoTargetResourceName },
        },
      },
    },
  ];

  adGroups.forEach((adGroup) => {
    const create = {
      resourceName: `customers/${customerId}/adGroups/${adGroupTempIds[adGroup.id]}`,
      campaign: `customers/${customerId}/campaigns/${campaignTempId}`,
      name: replaceStateText_(adGroup.name, target),
      status: adGroup.status || 'ENABLED',
      type: adGroup.type || 'SEARCH_STANDARD',
    };
    if (adGroup.cpcBidMicros) {
      create.cpcBidMicros = adGroup.cpcBidMicros;
    }
    operations.push({ adGroupOperation: { create } });
  });

  keywords.forEach((row) => {
    const criterion = row.adGroupCriterion;
    const keyword = criterion.keyword;
    if (shouldSkipSourceKeyword_(keyword.text)) {
      return;
    }
    targetKeywordTexts_(keyword.text, target).forEach((targetKeywordText) => {
      const create = {
        adGroup: `customers/${customerId}/adGroups/${adGroupTempIds[row.adGroup.id]}`,
        status: criterion.status || 'ENABLED',
        negative: Boolean(criterion.negative),
        keyword: {
          text: targetKeywordText,
          matchType: keyword.matchType || 'PHRASE',
        },
      };
      if (criterion.cpcBidMicros) {
        create.cpcBidMicros = criterion.cpcBidMicros;
      }
      const operation = { create };
      if (KEYWORD_POLICY_EXEMPTIONS[keyword.text]) {
        operation.exemptPolicyViolationKeys = KEYWORD_POLICY_EXEMPTIONS[keyword.text];
      }
      operations.push({ adGroupCriterionOperation: operation });
    });
  });

  adGroups.forEach((adGroup) => {
    STATE_CLONE_NEGATIVE_KEYWORDS.forEach((negativeText) => {
      operations.push({
        adGroupCriterionOperation: {
          create: {
            adGroup: `customers/${customerId}/adGroups/${adGroupTempIds[adGroup.id]}`,
            negative: true,
            keyword: {
              text: negativeText,
              matchType: 'BROAD',
            },
          },
        },
      });
    });
  });

  ads.forEach((row) => {
    const sourceAd = row.adGroupAd.ad;
    const rsa = sourceAd.responsiveSearchAd;
    const ad = {
      finalUrls: [buildTrackedSearchUrl_(target.landingPage, campaignName, adGroup.name, target)],
      responsiveSearchAd: {
        headlines: textAssets_(rsa.headlines || [], target),
        descriptions: textAssets_(rsa.descriptions || [], target),
      },
    };
    if (rsa.path1) {
      ad.responsiveSearchAd.path1 = replaceStateText_(rsa.path1, target);
    }
    if (rsa.path2) {
      ad.responsiveSearchAd.path2 = replaceStateText_(rsa.path2, target);
    }
    operations.push({
      adGroupAdOperation: {
        create: {
          adGroup: `customers/${customerId}/adGroups/${adGroupTempIds[row.adGroup.id]}`,
          status: 'PAUSED',
          ad,
        },
      },
    });
  });

  return operations;
}

function buildCampaignCreate_(customerId, campaignTempId, budgetTempId, campaignName, sourceCampaign) {
  const create = {
    resourceName: `customers/${customerId}/campaigns/${campaignTempId}`,
    name: campaignName,
    status: 'PAUSED',
    advertisingChannelType: 'SEARCH',
    containsEuPoliticalAdvertising: 'DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING',
    campaignBudget: `customers/${customerId}/campaignBudgets/${budgetTempId}`,
    networkSettings: copyKeys_(sourceCampaign.networkSettings || {}, [
      'targetGoogleSearch',
      'targetSearchNetwork',
      'targetContentNetwork',
      'targetPartnerSearchNetwork',
    ]),
    geoTargetTypeSetting: copyKeys_(sourceCampaign.geoTargetTypeSetting || {}, [
      'positiveGeoTargetType',
      'negativeGeoTargetType',
    ]),
  };

  Object.assign(create, biddingPayload_(sourceCampaign));
  ['trackingUrlTemplate', 'finalUrlSuffix'].forEach((key) => {
    if (sourceCampaign[key]) {
      create[key] = sourceCampaign[key];
    }
  });
  return create;
}

function biddingPayload_(sourceCampaign) {
  switch (sourceCampaign.biddingStrategyType) {
    case 'MANUAL_CPC':
      return { manualCpc: copyKeys_(sourceCampaign.manualCpc || {}, ['enhancedCpcEnabled']) };
    case 'MAXIMIZE_CONVERSIONS':
      return {
        maximizeConversions: copyKeys_(sourceCampaign.maximizeConversions || {}, ['targetCpaMicros']),
      };
    case 'MAXIMIZE_CONVERSION_VALUE':
      return {
        maximizeConversionValue: copyKeys_(sourceCampaign.maximizeConversionValue || {}, ['targetRoas']),
      };
    case 'TARGET_SPEND':
      return { targetSpend: copyKeys_(sourceCampaign.targetSpend || {}, ['cpcBidCeilingMicros']) };
    default:
      if (sourceCampaign.biddingStrategy) {
        return { biddingStrategy: sourceCampaign.biddingStrategy };
      }
      throw new Error(`Unsupported bidding strategy: ${sourceCampaign.biddingStrategyType}`);
  }
}

function textAssets_(assets, target) {
  return assets.map((asset) => {
    const copied = { text: replaceStateText_(asset.text, target) };
    if (asset.pinnedField) {
      copied.pinnedField = asset.pinnedField;
    }
    return copied;
  });
}

function shouldSkipSourceKeyword_(text) {
  return EXCLUDED_SOURCE_KEYWORD_PATTERNS.some((pattern) => pattern.test(text));
}

function targetKeywordTexts_(sourceText, target) {
  const replacement = STATE_KEYWORD_REPLACEMENTS[sourceText.toLowerCase()];
  if (replacement) {
    return replacement[target.state] || [replaceStateText_(sourceText, target)];
  }
  return [replaceStateText_(sourceText, target)];
}

function replaceStateText_(value, target) {
  return String(value)
    .replace(/\bServing Illinois and Indiana practices\b/g, `Serving ${target.state} practices`)
    .replace(/\bIllinois\b/g, target.state)
    .replace(/\billinois\b/g, target.state.toLowerCase())
    .replace(/\bIL\b/g, target.abbreviation);
}

function buildTrackedSearchUrl_(landingPage, campaignName, content, target) {
  const params = [
    ['utm_source', 'google'],
    ['utm_medium', 'paid_search'],
    ['utm_campaign', slugify_(campaignName)],
    ['utm_content', `${slugify_(replaceStateText_(content, target))}_ad_{creative}`],
    ['utm_audience', `${slugify_(target.state)}_state_search`],
    ['utm_id', '{campaignid}'],
    ['utm_term', '{keyword}'],
  ];
  const separator = String(landingPage).indexOf('?') === -1 ? '?' : '&';
  return String(landingPage) + separator + params.map(([key, value]) => {
    return `${encodeURIComponent(key)}=${encodeTrackingValue_(value)}`;
  }).join('&');
}

function encodeTrackingValue_(value) {
  return encodeURIComponent(value).replace(/%7B/g, '{').replace(/%7D/g, '}');
}

function slugify_(value) {
  const slug = String(value).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return slug || 'unknown';
}

function copyKeys_(source, keys) {
  const result = {};
  keys.forEach((key) => {
    if (source[key] !== undefined && source[key] !== null) {
      result[key] = source[key];
    }
  });
  return result;
}

function toRows_(query) {
  const iterator = AdsApp.search(query.replace(/\s+/g, ' ').trim(), { apiVersion: 'v24' });
  const rows = [];
  while (iterator.hasNext()) {
    rows.push(iterator.next());
  }
  return rows;
}

function escapeGaql_(value) {
  return String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}
